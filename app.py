import streamlit as st
import pandas as pd
from databricks import sql
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Guardiões do Ar - SCS", page_icon="🛡️", layout="centered")

# CSS para Identidade Visual (Mantido e ampliado com o health-card)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    div[data-testid="stMetricValue"] { color: #ff4b11 !important; }
    .stButton>button { 
        background-color: #ff4b11; color: white; border-radius: 20px; 
        border: none; height: 3em; font-weight: bold; width: 100%;
    }
    .health-card {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b11;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE DADOS (ORIGINAIS) ---

def get_db_connection():
    return sql.connect(
        server_hostname=st.secrets["db_hostname"],
        http_path=st.secrets["db_http_path"],
        access_token=st.secrets["db_token"]
    )

def salvar_missao(nome, pontos, ar, agua):
    query = "INSERT INTO default.guardioes_ar (nome, pontos, qualidade_ar, bebeu_agua, data) VALUES (?, ?, ?, ?, current_timestamp())"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (nome, pontos, ar, agua))

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
            if pts >= 150: return "🥇 Guardião Supremo"
            if pts >= 80:  return "🥈 Protetor"
            return "🥉 Recruta"
        df['Patente'] = df['xp_total'].apply(definir_patente)
        df = df.rename(columns={'nome': 'Patrulheiro', 'xp_total': 'XP'})
        return df[['Patente', 'Patrulheiro', 'XP']]
    return pd.DataFrame(columns=['Patente', 'Patrulheiro', 'XP'])

def ler_historico_ar():
    query = """
    SELECT 
        date_trunc('hour', data) as hora,
        AVG(CASE 
            WHEN qualidade_ar = 'Bom' THEN 1
            WHEN qualidade_ar = 'Regular' THEN 2
            WHEN qualidade_ar = 'Ruim' THEN 3
            WHEN qualidade_ar = 'Crítico' THEN 4
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

# --- 3. COMPONENTES VISUAIS NOVOS ---

def exibir_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        # Substitua pela URL do seu logo ou caminho local 'logo.png'
        st.image("LogoGuardioesDoAR.png", width=80) 
    with col2:
        st.title("Guardiões do Ar - SCS")

def secao_saude():
    with st.expander("🚨 ORIENTAÇÕES: Seca e Queimadas", expanded=False):
        st.markdown("### Como se proteger:")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="health-card"><strong>💧 Hidratação</strong><br>Beba água mesmo sem sede.</div>', unsafe_allow_html=True)
            st.markdown('<div class="health-card"><strong>🏠 Ar Interno</strong><br>Mantenha janelas fechadas se houver fumaça.</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="health-card"><strong>😷 Máscaras</strong><br>Use N95/PFF2 se a visibilidade estiver baixa.</div>', unsafe_allow_html=True)
            st.markdown('<div class="health-card"><strong>🏃 Exercícios</strong><br>Evite esforço físico entre 10h e 16h.</div>', unsafe_allow_html=True)
        
        st.link_button("Qualidade do Ar (IQAir)", "https://www.iqair.com/br/brazil")

# --- 4. INTERFACE PRINCIPAL ---

if 'user' not in st.session_state:
    exibir_header()
    nome_input = st.text_input("Codinome:", placeholder="Ex: Vigilante_SCS")
    if st.button("INICIAR PATRULHA"):
        if nome_input:
            st.session_state.user = nome_input
            st.rerun()
else:
    # Carregar dados
    df_ranking = ler_ranking_db()
    df_hist = ler_historico_ar()
    
    user_info = df_ranking[df_ranking['Patrulheiro'] == st.session_state.user]
    xp_atual = int(user_info['XP'].iloc[0]) if not user_info.empty else 0
    
    # Header e Saúde
    exibir_header()
    st.write(f"### Operação: **{st.session_state.user}**")
    secao_saude()
    
    st.metric("XP Acumulado", f"{xp_atual} pts")

    # FORMULÁRIO (Original)
    with st.form("form_missao", clear_on_submit=True):
        st.write("### 📝 Relatório de Campo")
        ar = st.select_slider("Como está o ar no SCS?", options=["Bom", "Regular", "Ruim", "Crítico"])
        agua = st.toggle("Bebi água 💧")
        
        btn_enviar = st.form_submit_button("REGISTRAR PATRULHA")
        
        if btn_enviar:
            pts = 10 + (5 if agua else 0)
            with st.spinner('Sincronizando com o Databricks...'):
                salvar_missao(st.session_state.user, pts, ar, "Sim" if agua else "Não")
                st.cache_data.clear()
            
            st.balloons()
            st.success(f"Excelente! +{pts} XP registrados.")
            time.sleep(2) 
            st.rerun()

    # GRÁFICO (Original)
    st.markdown("### 📊 Tendência de Poluição")
    if not df_hist.empty:
        df_plot = df_hist.copy()
        df_plot['hora_formatada'] = df_plot['hora'].dt.strftime('%H:%M')
        st.bar_chart(
            df_plot.set_index('hora_formatada')['nivel_medio'], 
            color="#ff4b11",
            width='stretch'
        )
        st.caption("Legenda: 1: Bom | 2: Regular | 3: Ruim | 4: Crítico")
    else:
        st.info("Aguardando mais registros para traçar o histórico...")
    
    # RANKING (Original)
    st.markdown("### 🏆 Top 10 Guardiões")
    st.dataframe(df_ranking.head(10), width='stretch', hide_index=True)

    if st.sidebar.button("Sair"):
        del st.session_state.user
        st.cache_data.clear()
        st.rerun()