import networkx as nx
import plotly.graph_objs as go
import plotly.io as pio
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objs as go
import json

def crear_grafica_lda(resultado_etiquetas, keyword="central_word", peso_umbral=0.00001, num_palabras=20):

    
    try:
        print("a")
        G = nx.Graph()

        G.add_node(keyword, size=75)

        word_topic_dict = {}
        for tema in resultado_etiquetas:
            nombre_tema = tema["Etiqueta"]
            palabras_clave = tema["Palabras_Clave"]

            palabras_seleccionadas = {palabra: peso for palabra, peso in palabras_clave.items() if peso >= peso_umbral}
            palabras_seleccionadas = dict(sorted(palabras_seleccionadas.items(), key=lambda item: item[1], reverse=True)[:num_palabras])

            G.add_node(nombre_tema, size=50)
            G.add_edge(keyword, nombre_tema, color='black')
            for palabra, peso in palabras_seleccionadas.items():
                G.add_node(palabra, size=25)
                if palabra in word_topic_dict:
                    word_topic_dict[palabra].append(nombre_tema)
                else:
                    word_topic_dict[palabra] = [nombre_tema]
                G.add_edge(nombre_tema, palabra, color='black', weight=round(peso, 1))

        for palabra, temas in word_topic_dict.items():
            if len(temas) > 1:
                for tema in temas:
                    G[tema][palabra]['color'] = 'indianred'

        pos = nx.spring_layout(G)
        print("b")
        
        edge_trace = []
        edge_labels = []
        for edge in G.edges(data=True):
            try:
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                peso = edge[2].get('weight', 1)
                print("b12")

                edge_trace.append(go.Scatter(
                    x=[x0, x1, None], y=[y0, y1, None],
                    line=dict(width=0.5, color=edge[2]['color']),
                    hoverinfo='none',
                    mode='lines'))
                print("b13")

                edge_labels.append(go.Scatter(
                    x=[(x0 + x1) / 2], y=[(y0 + y1) / 2],
                    text=[f'{peso:.1f}'],
                    mode='text',
                    hoverinfo='none',
                    showlegend=False))
            except Exception as e:
                print(f"⚠️ Error en el procesamiento de aristas: {e}")

        print("b14")
        node_trace = go.Scatter(
            x=[], y=[], text=[],
            mode='markers+text',
            hoverinfo='text',
            textposition='top center',
            marker=dict(
                showscale=True,
                colorscale='Viridis',
                size=[],
                color=[],
                colorbar=dict(
                    thickness=15,
                    title='Node Connections',
                    xanchor='left',
                    #titleside='right'
                ),
                line=dict(width=2)))
        
        print("c")
        
        for node in G.nodes():
            try:
                x, y = pos[node]
                node_trace['x'] += tuple([x])
                node_trace['y'] += tuple([y])
                node_trace['text'] += tuple([node])
                node_trace['marker']['size'] += tuple([G.nodes[node]['size']])
            except Exception as e:
                print(f"⚠️ Error en el procesamiento del nodo {node}: {e}")

        for node in G.nodes():
            try:
                if node == keyword:
                    node_trace['marker']['color'] += tuple(['red'])
                elif node in [tema["Etiqueta"] for tema in resultado_etiquetas]:
                    node_trace['marker']['color'] += tuple(['green'])
                else:
                    node_trace['marker']['color'] += tuple(['blue'])
            except Exception as e:
                print(f"⚠️ Error al asignar color a nodo {node}: {e}")

        fig = go.Figure(data=edge_trace + edge_labels + [node_trace],
                        layout=go.Layout(
                            title='<br>Visualización de Tópicos LDA',
                            #titlefont_size=16,
                            showlegend=False,
                            hovermode='closest',
                            paper_bgcolor='white',
                            plot_bgcolor='white',
                            font=dict(color='black'),
                            margin=dict(b=20, l=5, r=5, t=40),
                            annotations=[dict(
                                text="",
                                showarrow=False,
                                xref="paper", yref="paper")],
                            xaxis=dict(showgrid=False, zeroline=False),
                            yaxis=dict(showgrid=False, zeroline=False)))

        print("d")
        
        # Guardar la figura como HTML y devolver la ruta
        output_html = f"lda_graph_{keyword}.html"
        pio.write_html(fig, file=output_html, full_html=True)

        print("e")
        
        generarGrafica(resultado_etiquetas, keyword, peso_umbral)

        peso_umbral = 1.15

        generarGraficaSimplificada(resultado_etiquetas, peso_umbral)

        print("f")
        return output_html

    except Exception as e:
        print(f"🚨 Error general: {e}")
    


def generarGrafica(resultado_etiquetas, central_keyword, umbral_peso):
    # Definir la estructura de datos
    lda_result = resultado_etiquetas
    
    # Crear el grafo
    G = nx.Graph()
    
    # Agregar nodo central
    G.add_node(central_keyword)
    
    # Agregar etiquetas como nodos y conectar con la palabra clave central
    for topic in lda_result:
        topic_name = topic['Etiqueta']
        G.add_node(topic_name)
        G.add_edge(central_keyword, topic_name, weight=1.0)
        
        # Agregar palabras clave que superen el umbral como nodos y conectar con su etiqueta
        for term, weight in topic['Palabras_Clave'].items():
            if weight >= umbral_peso:
                G.add_node(term)
                G.add_edge(topic_name, term, weight=weight)
    
    # Obtener posiciones de los nodos con un diseño jerárquico
    pos = nx.spring_layout(G, seed=42, k=4, iterations=100)
    
    # Asignar colores a las conexiones basados en el peso
    edge_colors = []
    weights = []
    edge_labels = {}
    for src, dst in G.edges():
        weight = G[src][dst]['weight']
        weights.append(weight * 2)
        edge_labels[(src, dst)] = f"{weight:.1f}"
        
        if weight > 0.8:
            edge_colors.append("#00FF00")  # Verde fosforescente
        elif weight > 0.6:
            edge_colors.append("#FFFF00")  # Amarillo fosforescente
        elif weight > 0.3:
            edge_colors.append("#00FFFF")  # Cian fosforescente
        else:
            edge_colors.append("#FF00FF")  # Magenta fosforescente
    
    # Dibujar el grafo
    plt.figure(figsize=(10, 6), facecolor="black")
    ax = plt.gca()
    ax.set_facecolor("black")
    
    # Dibujar nodos primero para que estén debajo de las etiquetas
    nx.draw_networkx_nodes(G, pos, node_size=20, node_color="white")
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=weights)
    
    # Ajustar etiquetas para que no se superpongan con los nodos
    label_pos = {node: (x, y + 0.02) for node, (x, y) in pos.items()}  # Pequeño desplazamiento hacia arriba
    nx.draw_networkx_labels(G, label_pos, font_size=10, font_color="white", font_weight="bold", font_family="Arial")
    
    # Dibujar etiquetas de las aristas
    for (src, dst), label in edge_labels.items():
        x, y = (pos[src][0] + pos[dst][0]) / 2, (pos[src][1] + pos[dst][1]) / 2
        ax.text(x, y, label, fontsize=8, color="white", fontfamily="Arial",
                bbox=dict(facecolor="black", edgecolor="none", alpha=0.7),
                horizontalalignment="center", verticalalignment="center")
    
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig("./lda_topic_graph.png", dpi=300, facecolor="black", bbox_inches='tight')


def saltoLinea(texto):
    i=1
    newTexto = ''
    palabras = texto.split()

    for palabra in palabras:
        if(i%2 == 0):
            palabra = palabra + '\n'
        else:
            palabra = palabra + ' '
        newTexto += palabra
        
        i += 1
    
    return newTexto


def generarGraficaSimplificada(resultado_etiquetas, umbral_peso):
    pesos_relacionados = []
    lda_result = resultado_etiquetas
    G = nx.Graph()
    # Agregar tópicos y palabras clave
    for topic in lda_result:
        topic_name = saltoLinea(topic['Etiqueta'])
        G.add_node(topic_name, size=800, color='#00FF00', type='topic')
        
        for term, weight in topic['Palabras_Clave'].items():
            if weight >= umbral_peso:
                G.add_node(term, size=500, color='#00FF00', type='keyword')  # Cambiar a verde
                if(term in topic['Etiqueta']):
                    pesos_relacionados.append(weight)
                G.add_edge(topic_name, term, weight=weight, label=f"{weight:.2f}")

    pos = nx.spring_layout(
        G,
        seed=42,
        k=5.0,
        iterations=500,
        scale=8.0,
        weight=None
    )

    node_sizes  = [G.nodes[n]['size']   for n in G.nodes()]
    node_colors = [G.nodes[n]['color']  for n in G.nodes()]
    edge_weights= [2 for e in G.edges()]  # Grosor fijo para todas las aristas
    edge_labels = nx.get_edge_attributes(G, 'label')

    # Colores de aristas según peso
    edge_colors = []
    for src, dst in G.edges():
        w = G.edges[src, dst]['weight']
        if   w in pesos_relacionados: edge_colors.append("#00FF00")
        elif w > 0.6: edge_colors.append("#FFFF00")     # Amarillo para pesos medios
        else:         edge_colors.append("#4B0082")     # Morado oscuro para pesos bajos

    plt.figure(figsize=(16, 12), facecolor="black")
    ax = plt.gca()
    ax.set_facecolor("black")

    # Dibujar nodos y aristas
    nx.draw_networkx_nodes(G, pos,
                           node_size=node_sizes,
                           node_color=node_colors,
                           alpha=0.9,
                           edgecolors='white')
    nx.draw_networkx_edges(G, pos,
                           edge_color=edge_colors,
                           width=edge_weights,  # Usar grosor fijo
                           alpha=0.7)

    # Etiquetas de nodos SIN cajas, con texto encima del nodo
    for node, (x, y) in pos.items():
        attrs = G.nodes[node]
        offset = 0.35 if attrs['type'] == 'keyword' else 0.0  # Ajusta altura para keywords
        plt.text(x, y + offset, node,
                 fontsize=13 if attrs['type'] == 'topic' else 11,
                 fontweight='bold' if attrs['type'] == 'topic' else 'normal',
                 color='white', ha='center', va='bottom')

    # Etiquetas de aristas desplazadas perpendicularmente
    for (src, dst), label in edge_labels.items():
        x1, y1 = pos[src]
        x2, y2 = pos[dst]
        dx, dy = x2 - x1, y2 - y1
        dist = (dx**2 + dy**2)**0.5
        if dist == 0: continue
        perp = (-dy/dist*0.15, dx/dist*0.15)
        mx, my = (x1 + x2)/2 + perp[0], (y1 + y2)/2 + perp[1]
        plt.text(mx, my, label, fontsize=11, color='white', fontweight='bold',
                 ha='center', va='center')

    plt.axis('off')
    plt.tight_layout()
    plt.savefig("./lda_topic_graph_simplified.png", dpi=300,
                facecolor="black", bbox_inches='tight')
    


