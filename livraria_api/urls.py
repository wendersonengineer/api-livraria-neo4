from django.urls import path
from . import views

urlpatterns = [
    path('livros/', views.listar_livros, name='listar_livros'),
    path('livros/<int:pk>/', views.detalhar_livro, name='detalhar_livro'),
    path('clientes/', views.criar_cliente, name='criar_cliente'),
    path('pedidos/', views.criar_pedido, name='criar_pedido'),
    path('relatorios/mais-vendidos/', views.relatorio_mais_vendidos, name='mais_vendidos'),
    path('livros/filtrar-por-preco/', views.filtrar_livros_por_preco, name='filtrar_por_preco'),
]
