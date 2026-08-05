-- Dados de exemplo (produtos) para testar a automação
INSERT INTO produtos (nome, categoria, custo_unitario, preco_venda, quantidade_estoque, estoque_minimo) VALUES
('Camiseta Basica Branca',   'Vestuario',  18.00, 45.00, 40, 10),
('Camiseta Estampada Preta', 'Vestuario',  22.00, 55.00,  6, 10),
('Caneca Personalizada',     'Presentes', 12.50, 32.00,  3, 8),
('Garrafa Termica 500ml',    'Presentes', 28.00, 69.90, 15, 5),
('Bone Aba Reta',            'Vestuario',  15.00, 39.90,  2, 6)
ON CONFLICT DO NOTHING;
