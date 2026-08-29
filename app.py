import streamlit as st
import pandas as pd
from databricks import sql
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Eco Pontos - SBS", page_icon="🌱", layout="centered")

# CSS para Identidade Visual (Verde Ecológico)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    div[data-testid="stMetricValue"] { color: #2e7d32 !important; }
    .stButton>button { 
        background-color: #2e7d32; color: white; border-radius: 20px; 
        border: none; height: 3em; font-weight: bold; width: 100%;
    }
    .health-card {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2e7d32;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE DADOS ---

def get_db_connection():
    return sql.connect(
        server_hostname=st.secrets["db_hostname"],
        http_path=st.secrets["db_http_path"],
        access_token=st.secrets["db_token"]
    )

def salvar_missao(nome, pontos, reciclagem, descarte):
    query = "INSERT INTO default.guardioes_ar (nome, pontos, qualidade_ar, bebeu_agua, data) VALUES (?, ?, ?, ?, current_timestamp())"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (nome, pontos, reciclagem, descarte))

@st.cache_data(ttl=2)
def ler_ranking_db():
    query = "SELECT nome, SUM(pontos) as xp_total FROM default.guardioes_ar GROUP BY nome ORDER BY xp_total DESC"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=cols)
    
    if not df.empty:
        def definir_patente(pts):
            if pts >= 150: return "🥇 Eco Guardião"
            if pts >= 80:  return "🥈 Reciclador"
            return "🥉 Agente Verde"
        df['Patente'] = df['xp_total'].apply(definir_patente)
        df = df.rename(columns={'nome': 'Participante', 'xp_total': 'Pontos'})
        return df[['Patente', 'Participante', 'Pontos']]
    return pd.DataFrame(columns=['Patente', 'Participante', 'Pontos'])

def ler_historico_ar():
    query = """
    SELECT 
        date_trunc('hour', data) as hora,
        AVG(CASE 
            WHEN qualidade_ar = 'Excelente' THEN 1
            WHEN qualidade_ar = 'Bom' THEN 2
            WHEN qualidade_ar = 'Pouco' THEN 3
            WHEN qualidade_ar = 'Nenhum' THEN 4
            ELSE 1 END) as nivel_medio
    FROM default.guardioes_ar
    GROUP BY 1 ORDER BY 1 ASC
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=cols)
    
    if not df.empty:
        df['hora'] = pd.to_datetime(df['hora'])
    return df

# --- 3. COMPONENTES VISUAIS ---

def exibir_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("LogoEcoPontos.png", width=80) 
    with col2:
        st.title("Eco Pontos - SBS")

def secao_saude():
    with st.expander("♻️ GUIA: Reciclagem no SBS", expanded=False):
        st.markdown("### Dicas de Sustentabilidade:")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="health-card"><strong>📦 Papel e Papelão</strong><br>Descarte limpo e seco nos PEVs.</div>', unsafe_allow_html=True)
            st.markdown('<div class="health-card"><strong>🥤 Plásticos</strong><br>Higienize antes do descarte.</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="health-card"><strong>🔋 Eletrônicos</strong><br>Entregue em pontos específicos no SBS.</div>', unsafe_allow_html=True)
            st.markdown('<div class="health-card"><strong>🌱 Orgânicos</strong><br>Separe para compostagem local.</div>', unsafe_allow_html=True)
        
        st.link_button("Pontos de Coleta (SLU DF)", "https://www.slu.df.gov.br/")

# --- 4. INTERFACE PRINCIPAL ---

if 'user' not in st.session_state:
    exibir_header()
    nome_input = st.text_input("Codinome:", placeholder="Ex: Eco_Agente_SBS")
    if st.button("REGISTRAR ECO AÇÃO"):
        if nome_input:
            st.session_state.user = nome_input
            st.rerun()
else:
    # Carregar dados
    df_ranking = ler_ranking_db()
    df_hist = ler_historico_ar()
    
    user_info = df_ranking[df_ranking['Participante'] == st.session_state.user]
    xp_atual = int(user_info['Pontos'].iloc[0]) if not user_info.empty else 0
    
    # Header e Saúde
    exibir_header()
    st.write(f"### Operação: **{st.session_state.user}**")
    secao_saude()
    
    st.metric("Eco Pontos Acumulados", f"{xp_atual} pts")

    # FORMULÁRIO (Mantida a mesma lógica e colunas da tabela SQL)
    with st.form("form_missao", clear_on_submit=True):
        st.write("### 📝 Registro de Descarte / Coleta")
        ar = st.select_slider("Volume de resíduos reciclados hoje:", options=["Excelente", "Bom", "Pouco", "Nenhum"])
        agua = st.toggle("Descartei no EcoPonto correto ♻️")
        
        btn_enviar = st.form_submit_button("REGISTRAR ECO AÇÃO")
        
        if btn_enviar:
            pts = 10 + (5 if agua else 0)
            with st.spinner('Sincronizando com o Databricks...'):
                salvar_missao(st.session_state.user, pts, ar, "Sim" if agua else "Não")
                st.cache_data.clear()
            
            st.balloons()
            st.success(f"Excelente! +{pts} Eco Pontos registrados.")
            time.sleep(2) 
            st.rerun()

    # GRÁFICO
    st.markdown("### 📊 Índice de Descarte Reciclável")
    if not df_hist.empty:
        df_plot = df_hist.copy()
        df_plot['hora_formatada'] = df_plot['hora'].dt.strftime('%H:%M')
        st.bar_chart(
            df_plot.set_index('hora_formatada')['nivel_medio'], 
            color="#2e7d32",
            width='stretch'
        )
        st.caption("Legenda: 1: Excelente | 2: Bom | 3: Pouco | 4: Nenhum")
    else:
        st.info("Aguardando mais registros para traçar o histórico...")
    
    # RANKING
    st.markdown("### 🏆 Top 10 Eco Agentes")
    st.dataframe(df_ranking.head(10), width='stretch', hide_index=True)

    if st.sidebar.button("Sair"):
        del st.session_state.user
        st.cache_data.clear()
        st.rerun()
