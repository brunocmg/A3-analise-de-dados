import concurrent.futures
import csv
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

def obter_produtos_da_pagina(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        itens = soup.find_all('li', class_='promotion-item')

        produtos = []

        for item in itens:
            nome_elemento = item.find('p', class_='promotion-item__title')
            preco_original_elemento = item.find('span', class_='andes-money-amount__fraction')
            desconto_elemento = item.find('span', class_='promotion-item__discount-text')

            if not all([nome_elemento, preco_original_elemento]):
                continue

            preco_original_texto = preco_original_elemento.text.strip().replace('.', '').replace(',', '.')
            preco_original = float(preco_original_texto) if preco_original_texto else 0

            desconto = 0
            if desconto_elemento:
                desconto_texto = ''.join(filter(str.isdigit, desconto_elemento.text))
                if desconto_texto:
                    desconto = float(desconto_texto) / 100
            
            valor_final = preco_original * (1 - desconto)

            if desconto > 0.15:
                produtos.append({
                    'Nome': nome_elemento.text.strip(),
                    'Preço Original': preco_original,
                    'Desconto': desconto_elemento.text.strip() if desconto_elemento else '0% OFF',
                    'Valor Final': valor_final
                })
        
        return produtos
    except requests.RequestException as e:
        print(f"Erro ao acessar a página {url}: {e}")
        return []

def obter_todos_produtos():
    url_base = 'https://www.mercadolivre.com.br/ofertas?page='
    todos_produtos = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        urls = [url_base + str(pagina) for pagina in range(1, 21)]
        future_to_url = {executor.submit(obter_produtos_da_pagina, url): url for url in urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                produtos_da_pagina = future.result()
                if produtos_da_pagina:
                    todos_produtos.extend(produtos_da_pagina)
            except Exception as exc:
                print(f'A página gerou uma exceção: {exc}')
                
    return todos_produtos

def gerar_csv(produtos, nome_arquivo):
    if not produtos:
        print("Nenhum produto para salvar no CSV.")
        return
        
    campos = ['Nome', 'Preço Original', 'Desconto', 'Valor Final']
    with open(nome_arquivo, mode='w', newline='', encoding='utf-8') as arquivo_csv:
        escritor_csv = csv.DictWriter(arquivo_csv, fieldnames=campos)
        escritor_csv.writeheader()
        escritor_csv.writerows(produtos)

def gerar_excel(produtos, nome_arquivo_excel):

    if not produtos:
        print("Nenhum produto para salvar no Excel.")
        return

    df = pd.DataFrame(produtos)
    
    df['Preço Original'] = df['Preço Original'].map('R$ {:,.2f}'.format)
    df['Valor Final'] = df['Valor Final'].map('R$ {:,.2f}'.format)

    df.to_excel(nome_arquivo_excel, index=False)

def gerar_boxplot(produtos):
    if not produtos:
        print("Nenhum produto para gerar o gráfico.")
        return
        
    valores_finais = [produto['Valor Final'] for produto in produtos]
    
    media = np.mean(valores_finais)
    mediana = np.median(valores_finais)
    desvio_padrao = np.std(valores_finais)
    
    Q1 = np.percentile(valores_finais, 25)
    Q3 = np.percentile(valores_finais, 75)
    IQR = Q3 - Q1
    lim_inf = Q1 - 1.5 * IQR
    lim_sup = Q3 + 1.5 * IQR
    outliers = sum((x < lim_inf or x > lim_sup) for x in valores_finais)
    
    plt.figure(figsize=(10, 7))
    plt.boxplot(valores_finais, vert=True)
    plt.title('Boxplot dos Preços Finais dos Produtos em Oferta')
    plt.ylabel('Preço (R$)')
    plt.xticks([1], ['Produtos']) 

    plt.axhline(y=media, color='r', linestyle='--', label=f'Média: R$ {media:.2f}')
    plt.axhline(y=mediana, color='g', linestyle='--', label=f'Mediana: R$ {mediana:.2f}')
    
    info_texto = (f'Desvio Padrão: R$ {desvio_padrao:.2f}\n'
                  f'Outliers: {outliers}')
    plt.figtext(0.15, 0.15, info_texto, bbox={"facecolor":"orange", "alpha":0.5, "pad":5})

    plt.legend()
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.show()

def main():
    print("Iniciando a busca por produtos...")
    produtos = obter_todos_produtos()
    
    if produtos:
        print(f"{len(produtos)} produtos encontrados com mais de 15% de desconto.")
        
        produtos.sort(key=lambda x: x['Nome'])
        
        nome_arquivo_csv = 'produtos.csv'
        gerar_csv(produtos, nome_arquivo_csv)
        print(f"Arquivo CSV '{nome_arquivo_csv}' gerado com sucesso!")
        
        nome_arquivo_excel = 'produtos.xlsx'
        gerar_excel(produtos, nome_arquivo_excel)
        print(f"Arquivo Excel '{nome_arquivo_excel}' gerado com sucesso!")
        
        print("Gerando o gráfico boxplot...")
        gerar_boxplot(produtos)
    else:
        print("Nenhum produto encontrado que corresponda aos critérios.")

if __name__ == "__main__":
    main()