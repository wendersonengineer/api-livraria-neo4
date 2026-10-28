from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils import Neo4jConnection

# Puxa a conexão master compartilhada do Neo4j
driver = Neo4jConnection.get_driver()

# ─── [ROTA 1] GET /api/livros/ ──────────────────────────────────────────────
@api_view(['GET'])
def listar_livros(request):
    """Lista todos os livros (nós :Livro) cadastrados no grafo."""
    query = "MATCH (l:Livro) RETURN l.id AS id, l.titulo AS titulo, l.preco AS preco"
    with driver.session() as session:
        result = session.run(query)
        dados = [record.data() for record in result]

        return Response(dados, status=status.HTTP_200_OK)


# ─── [ROTA 2] GET /api/livros/<id>/ ──────────────────────────────────────────
@api_view(['GET'])
def detalhar_livro(request, pk):
    """Detalhe de um livro com Autor e Categoria através de travessia de relacionamentos."""
    query = """
    MATCH (l:Livro {id: $id})
    OPTIONAL MATCH (l)-[:ESCRITO_POR]->(a:Autor)
    OPTIONAL MATCH (l)-[:PERTENCE_A]->(c:Categoria)
    RETURN l.id AS id, l.titulo AS titulo, l.preco AS preco, l.isbn AS isbn,
           l.ano_publicacao AS ano_publicacao, l.avaliacao_media AS avaliacao_media,
           {id: a.id, nome: a.nome, nacionalidade: a.nacionalidade} AS autor,
           {id: c.id, nome: c.nome, descricao: c.descricao} AS categoria
    """
    with driver.session() as session:
        result = session.run(query, id=int(pk))
        record = result.single()
        if not record:
            return Response({"detail": "Livro não encontrado no grafo"}, status=status.HTTP_404_NOT_FOUND)
        return Response(dict(record), status=status.HTTP_200_OK)


# ─── [ROTA 3] POST /api/clientes/ ────────────────────────────────────────────
@api_view(['POST'])
def criar_cliente(request):
    """Cria ou atualiza um nó :Cliente a partir do corpo da requisição."""
    dados = request.data
    query = """
    MERGE (c:Cliente {id: $id})
    ON CREATE SET c.nome = $nome, c.email = $email, c.cidade = $cidade, 
                  c.estado = $estado, c.membro_desde = $membro_desde
    ON MATCH SET c.nome = $nome, c.email = $email
    RETURN c.id AS id, c.nome AS nome
    """
    try:
        with driver.session() as session:
            result = session.run(
                query, id=int(dados['id']), nome=dados['nome'], email=dados['email'],
                cidade=dados['cidade'], estado=dados['estado'], membro_desde=dados['membro_desde']
            )
            return Response({"status": "sucesso", "cliente": dict(result.single())}, status=status.HTTP_201_CREATED)
    except KeyError as e:
        return Response({"detail": f"Campo obrigatório ausente: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)



# ─── [ROTA 4] POST /api/pedidos/ ─────────────────────────────────────────────
@api_view(['POST'])
def criar_pedido(request):
    """Cria um :Pedido conectado a um :Cliente e a múltiplos :Livro com propriedades."""
    dados = request.data
    pedido_id = int(dados['id'])
    cliente_id = int(dados['cliente_id'])
    
    with driver.session() as session:
        # Validação defensiva obrigatória: O cliente realmente existe no grafo?
        check_cliente = session.run("MATCH (c:Cliente {id: $c_id}) RETURN c", c_id=cliente_id)
        if not check_cliente.single():
            return Response({"detail": f"Erro: Cliente com ID {cliente_id} não existe no grafo."}, status=status.HTTP_400_BAD_REQUEST)

        # Calcula o valor total do pedido baseado na lista de itens recebida
        total_calculado = sum(float(item['quantidade']) * float(item['preco_unitario']) for item in dados['itens'])

        # Cria o nó do Pedido e passa a linha física [:FEITO_POR] para o Cliente existente
        query_pedido = """
        MERGE (p:Pedido {id: $id})
        SET p.data_pedido = $data_pedido, p.status = $status, p.total = $total
        WITH p
        MATCH (c:Cliente {id: $cliente_id})
        MERGE (p)-[:FEITO_POR]->(c)
        RETURN p
        """
        session.run(query_pedido, id=pedido_id, data_pedido=dados['data_pedido'], 
                    status=dados['status'], total=total_calculado, cliente_id=cliente_id)

        # Mapeia as arestas de relacionamento [:CONTEM] com atributos para cada livro comprado
        query_item = """
        MATCH (p:Pedido {id: $pedido_id})
        MATCH (l:Livro {id: $livro_id})
        MERGE (p)-[r:CONTEM {livro_id: $livro_id}]->(l)
        SET r.quantidade = $quantidade, r.preco_unitario = $preco_unitario
        """
        for item in dados['itens']:
            livro_id = int(item['livro_id'])
            
            # Validação defensiva obrigatória: O livro realmente existe no grafo?
            check_livro = session.run("MATCH (l:Livro {id: $l_id}) RETURN l", l_id=livro_id)
            if not check_livro.single():
                return Response({"detail": f"Erro: Livro com ID {livro_id} não existe no grafo."}, status=status.HTTP_400_BAD_REQUEST)
            
            session.run(query_item, pedido_id=pedido_id, livro_id=livro_id, 
                        quantidade=int(item['quantidade']), preco_unitario=float(item['preco_unitario']))

        return Response({"status": "pedido_criado", "id": pedido_id, "total": total_calculado}, status=status.HTTP_201_CREATED)


# ─── [ROTA 5] GET /api/relatorios/mais-vendidos/ ─────────────────────────────
@api_view(['GET'])
def relatorio_mais_vendidos(request):
    """Retorna os livros mais vendidos por categoria (Query de Agregação Cypher)."""
    query = """
    MATCH (p:Pedido {status: 'entregue'})-[ip:CONTEM]->(l:Livro)-[:PERTENCE_A]->(c:Categoria)
    RETURN c.nome AS categoria, l.titulo AS livro, sum(ip.quantidade) AS total_vendido
    ORDER BY total_vendido DESC
    LIMIT 5
    """
    with driver.session() as session:
        result = session.run(query)
        dados = [dict(record) for record in result]
        return Response(dados, status=status.HTTP_200_OK)


# ─── [ROTA EXTRA] GET /api/livros/filtrar-por-preco/ ─────────────────────────
@api_view(['GET'])
def filtrar_livros_por_preco(request):
    """Filtra livros por valor máximo passado via parâmetro de busca (Ex: ?max=45.50)."""
    preco_maximo = float(request.query_params.get('max', 50.0))
    query = """
    MATCH (l:Livro)
    WHERE l.preco <= $preco_maximo
    RETURN l.id AS id, l.titulo AS titulo, l.preco AS preco
    ORDER BY l.preco ASC
    """
    with driver.session() as session:
        result = session.run(query, preco_maximo=preco_maximo)
        dados = [dict(record) for record in result]
        return Response(dados, status=status.HTTP_200_OK)