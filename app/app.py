"""Dashboard do Projeto Extensionista — Enchentes em Porto Alegre (INCT SiMAI).

Rodar a partir da raiz do repositório:
    streamlit run app/app.py
"""
import streamlit as st

st.set_page_config(page_title="Enchentes em Porto Alegre", page_icon="💧", layout="wide")

pagina = st.navigation([
    st.Page("tela1_simulacao.py", title="1. Simulação do INCT", icon="🌊", default=True),
    st.Page("tela2_bases.py", title="2. Equipamentos e abastecimento", icon="🏫"),
    st.Page("tela3_abastecimento.py", title="3. Abastecimento de água", icon="🚰"),
    st.Page("tela4_educacao.py", title="4. Educação", icon="📊"),
    st.Page("tela5_vulnerabilidade.py", title="5. Vulnerabilidade por bairro", icon="📍"),
])

st.sidebar.caption("Projeto Extensionista · Coleta, Preparação e Análise de Dados · PUCRS")
st.sidebar.caption("Os números são estimativas de uma simulação, não previsões nem contagens oficiais.")

pagina.run()
