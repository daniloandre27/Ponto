import os
import pickle
import pandas as pd
import time as tm
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import streamlit.components.v1 as components
from datetime import datetime, timedelta


# Escopo para acesso ao Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Função para autenticação usando OAuth2
def autenticar_google_calendar():
    credenciais = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credenciais = pickle.load(token)

    if not credenciais or not credenciais.valid:
        if credenciais and credenciais.expired and credenciais.refresh_token:
            credenciais.refresh(Request())
        else:
            fluxo = InstalledAppFlow.from_client_secrets_file(
                'AutenticaCalendar.json', SCOPES
            )
            credenciais = fluxo.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(credenciais, token)
    
    return credenciais
# Função para obter o ID do calendário autenticado
def obter_id_calendario(credenciais):
    servico = build('calendar', 'v3', credentials=credenciais)
    calendario = servico.calendars().get(calendarId='primary').execute()
    return calendario['id']

#
def adicionar_evento_calendario(servico, calendario_id, titulo, inicio, fim, emails_convidados=None):
    """Adiciona um evento ao Google Calendar."""
    try:
        evento = {
            'summary': titulo,  # Título do evento
            'start': {'dateTime': inicio, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': fim, 'timeZone': 'America/Sao_Paulo'},
            'attendees': [{'email': email} for email in emails_convidados] if emails_convidados else [],
        }
        # Envia o evento para o Google Calendar
        servico.events().insert(calendarId=calendario_id, body=evento).execute()
    except Exception as e:
        raise Exception(f"Erro ao criar evento no Google Calendar: {e}")


def exibir_formulario_ferias():
    from new import obter_conexao_persistente  # Importação necessária

    # Autenticar e obter credenciais para o Google Calendar
    creds = autenticar_google_calendar()
    calendario_id = obter_id_calendario(creds)
    servico = build('calendar', 'v3', credentials=creds)

    st.markdown("<h1 style='text-align: center;'>Marcar Férias</h1>", unsafe_allow_html=True)

    # Obter lista de funcionários com seus e-mails do banco
    conn = obter_conexao_persistente()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ID, NOME, EMAIL
                FROM FUNCIONARIOS
                ORDER BY 2
            """)
            funcionarios = cursor.fetchall()  # Retorna [(ID, Nome, Username, Email)]
        except Exception as e:
            st.error(f"Erro ao carregar os funcionários: {e}")
            return
    else:
        st.error("Erro na conexão com o banco de dados.")
        return

    if not funcionarios:
        st.error("Nenhum funcionário encontrado no banco de dados.")
        return

    # Criar um dicionário para mapear o nome para ID e e-mail
    funcionarios_dict = {
        f"{nome}": {"id": id, "email": email} for id, nome, email in funcionarios
    }

    # Inicializar o estado, se necessário
    if "funcionario_selecionado" not in st.session_state:
        primeiro_funcionario = list(funcionarios_dict.keys())[0]
        st.session_state["funcionario_selecionado"] = primeiro_funcionario
        st.session_state["emails_convidados"] = funcionarios_dict[primeiro_funcionario]["email"] or ""

    # Atualizar o funcionário selecionado
    funcionario_selecionado = st.selectbox(
        "Selecione o Funcionário",
        options=list(funcionarios_dict.keys()),
        index=list(funcionarios_dict.keys()).index(st.session_state["funcionario_selecionado"]),
        on_change=lambda: update_emails_convidados(funcionarios_dict),
        key="funcionario_selecionado",
    )

    def update_emails_convidados(funcionarios_dict):
        """Atualiza os e-mails convidados no estado ao mudar o funcionário."""
        email = funcionarios_dict[st.session_state["funcionario_selecionado"]]["email"]
        st.session_state["emails_convidados"] = email or ""

    # Formulário para preenchimento dos dados
    with st.form("formulario_ferias"):
        data_inicio = st.date_input("Data de Início", format="DD/MM/YYYY")
        data_fim = st.date_input("Data de Fim", format="DD/MM/YYYY")
        emails_convidados = st.text_area(
            "E-mails dos Envolvidos (separados por vírgula)",
            value=st.session_state.get("emails_convidados", ""),
            placeholder="exemplo1@dominio.com, exemplo2@dominio.com",
            key="emails_convidados",
        )
        botao_submeter = st.form_submit_button("Marcar Férias")

        if botao_submeter:
            if data_inicio > data_fim:
                st.error("A data de início não pode ser maior que a data de fim.")
            elif not funcionario_selecionado:
                st.error("O funcionário é obrigatório.")
            else:
                # Obter o ID do funcionário selecionado
                funcionario_id = funcionarios_dict[funcionario_selecionado]["id"]
                titulo = f"Férias: {funcionario_selecionado.split(' ')[0]}"
                emails_formatados = [email.strip() for email in emails_convidados.split(",") if email.strip()]

                # Adicionar ao Google Calendar
                adicionar_evento_calendario(
                    servico,
                    calendario_id,
                    titulo,
                    data_inicio.strftime('%Y-%m-%d'),
                    (data_fim + timedelta(days=1)).strftime('%Y-%m-%d'),  # Inclui o último dia
                    emails_formatados,
                )

                # Inserir no banco de dados
                if conn:
                    try:
                        cursor.execute("""
                            INSERT INTO FERIAS (FUNCIONARIO_ID, DATA_INICIO, DATA_FIM, EMAILS_ENVOLVIDOS)
                            VALUES (?, ?, ?, ?)
                        """, (funcionario_id, data_inicio, data_fim, ','.join(emails_formatados)))
                        conn.commit()
                        st.success(f"Férias de {funcionario_selecionado.split(' ')[0]} adicionadas ao calendário e salvas no banco de dados!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco de dados: {e}")



def minhas_ferias_marcadas():
    from new import obter_conexao_persistente
    usuario = st.session_state["usuario"]
    st.markdown("<h1 style='text-align: center;'>Minhas Férias</h1>", unsafe_allow_html=True)

    # Obter a conexão com o banco de dados
    conn = obter_conexao_persistente()
    if conn:
        try:
            cursor = conn.cursor()
            # Buscar todas as férias marcadas
            cursor.execute("""
                SELECT 
                    f.NOME AS Funcionario,
                    ferias.DATA_INICIO AS DataInicio,
                    ferias.DATA_FIM AS DataFim,
                    ferias.REGISTRADO_EM AS RegistradoEm
                FROM FERIAS ferias
                JOIN FUNCIONARIOS f ON ferias.FUNCIONARIO_ID = f.ID
                WHERE FUNCIONARIO_ID = ?
                ORDER BY ferias.DATA_INICIO DESC
            """,(usuario["id"],))
            registros = cursor.fetchall()

            if registros:
                # Criar o DataFrame para exibir os dados
                df = pd.DataFrame(
                    registros,
                    columns=["Funcionário", "Data de Início", "Data Final","Aprovado em"]
                )

                # Formatando as colunas de data para exibição
                df["Data de Início"] = pd.to_datetime(df["Data de Início"]).dt.strftime("%d/%m/%Y")
                df["Data Final"] = pd.to_datetime(df["Data Final"]).dt.strftime("%d/%m/%Y")
                df["Aprovado em"] = pd.to_datetime(df["Aprovado em"]).dt.strftime("%d/%m/%Y")

                # Exibir o DataFrame no Streamlit
                st.dataframe(df,hide_index=True,use_container_width=True )

            else:
                st.warning("Nenhuma férias marcada no momento.")
        except Exception as e:
            st.error(f"Erro ao buscar férias marcadas: {e}")
        finally:
            ''
    else:
        st.error("Erro na conexão com o banco de dados.")

def ferias_marcadas():
    from new import obter_conexao_persistente, conexao_persistente
    st.markdown("<h1 style='text-align: center;'>Férias Agendadas</h1>", unsafe_allow_html=True)

    # Obter a conexão com o banco de dados
    conn = conexao_persistente
    if conn:
        try:
            cursor = conexao_persistente.cursor()
            # Buscar todas as férias marcadas
            cursor.execute("""
                SELECT 
                    f.NOME AS Funcionario,
                    ferias.DATA_INICIO AS DataInicio,
                    ferias.DATA_FIM AS DataFim,
                    ferias.REGISTRADO_EM AS RegistradoEm
                FROM FERIAS ferias
                JOIN FUNCIONARIOS f ON ferias.FUNCIONARIO_ID = f.ID
                ORDER BY 1
            """)
            registros = cursor.fetchall()

            if registros:
                # Criar o DataFrame para exibir os dados
                df = pd.DataFrame(
                    registros,
                    columns=["Funcionário", "Data de Início", "Data Final","Aprovado em"]
                )

                # Formatando as colunas de data para exibição
                df["Data de Início"] = pd.to_datetime(df["Data de Início"]).dt.strftime("%d/%m/%Y")
                df["Data Final"] = pd.to_datetime(df["Data Final"]).dt.strftime("%d/%m/%Y")
                df["Aprovado em"] = pd.to_datetime(df["Aprovado em"]).dt.strftime("%d/%m/%Y")

                # Exibir o DataFrame no Streamlit
                st.dataframe(df,hide_index=True,use_container_width=True )

            else:
                st.warning("Nenhuma férias marcada no momento.")
        except Exception as e:
            st.error(f"Erro ao buscar férias marcadas: {e}")
        finally:
            ''
    else:
        st.error("Erro na conexão com o banco de dados.")

def add_evento():
    from new import obter_conexao_persistente  # Importação necessária

    # Autenticar e obter credenciais para o Google Calendar
    creds = autenticar_google_calendar()
    calendario_id = obter_id_calendario(creds)
    servico = build('calendar', 'v3', credentials=creds)

    st.markdown("<h1 style='text-align: center;'>Agendamento</h1>", unsafe_allow_html=True)

    # Obter lista de funcionários com seus e-mails do banco
    conn = obter_conexao_persistente()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ID, NOME, EMAIL
                FROM FUNCIONARIOS
                ORDER BY 2
            """)
            funcionarios = cursor.fetchall()  # Retorna [(ID, Nome, Email)]
        except Exception as e:
            st.error(f"Erro ao carregar os funcionários: {e}")
            return
    else:
        st.error("Erro na conexão com o banco de dados.")
        return

    if not funcionarios:
        st.error("Nenhum funcionário encontrado no banco de dados.")
        return

    # Criar um dicionário para mapear o nome para ID e e-mail
    funcionarios_dict = {
        nome: {"id": id, "email": email} for id, nome, email in funcionarios
    }

    # Seleção de múltiplos funcionários
    funcionarios_selecionados = st.multiselect(
        "",
        help=None,
        options=list(funcionarios_dict.keys()),
        placeholder="Selecione os Funcionários"
    )

    # Obter os e-mails dos funcionários selecionados
    emails_funcionarios_selecionados = [
        funcionarios_dict[funcionario]["email"]
        for funcionario in funcionarios_selecionados
    ]

    # Formulário para preenchimento dos dados
    with st.form("agendamento"):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", format="DD/MM/YYYY")
        with col2:
            titulo = st.text_input("Título",placeholder="Digite o título da reunião",help="Insira um título descritivo para o agendamento.")

        col3, col4 = st.columns(2)
        with col3:
            hora_inicio = st.time_input("Hora de Início", key="hora_inicio")
        with col4:
            hora_fim = st.time_input("Hora de Fim", key="hora_fim")

        # Preencher o campo de e-mails com os e-mails dos funcionários selecionados
        emails_convidados = st.text_area(
            "E-mails dos Envolvidos (separados por vírgula)",
            value=", ".join(emails_funcionarios_selecionados),  # Usa os e-mails obtidos
            placeholder="exemplo1@dominio.com, exemplo2@dominio.com",
            key="emails_convidados",
        )

        botao_submeter = st.form_submit_button("Agendar",use_container_width=True)
        
    if botao_submeter:
        emails_formatados = [email.strip() for email in emails_convidados.split(",") if email.strip()]

        if not titulo or not emails_formatados:
            st.error("Título e e-mails dos envolvidos são obrigatórios.")
        elif hora_inicio >= hora_fim:
            st.error("A hora de início deve ser menor que a hora de fim.")
        else:
            try:
                # Formatar os horários para o formato ISO 8601
                inicio = f"{data.strftime('%Y-%m-%d')}T{hora_inicio.strftime('%H:%M:%S')}"
                fim = f"{data.strftime('%Y-%m-%d')}T{hora_fim.strftime('%H:%M:%S')}"

                # Adicionar ao Google Calendar
                adicionar_evento_calendario(
                    servico,
                    calendario_id,
                    titulo,
                    inicio,
                    fim,
                    emails_formatados,
                )
                placeholder = st.empty() 
                placeholder.success(f"Evento agendado com sucesso!", icon="✅")
                tm.sleep(2)
                placeholder.empty()
            except Exception as e:
                st.error(f"Erro ao agendar evento: {e}")




# Função para exibição do Google Calendar
def exibir_calendario():
    st.markdown("<h1 style='text-align: center;'>Agenda</h1>", unsafe_allow_html=True)

    calendar_html = '''
    <iframe src="https://calendar.google.com/calendar/embed?height=600&wkst=1&ctz=America%2FSao_Paulo&src=ZGFuaWxvYW5kcmUyN0BnbWFpbC5jb20&color=%234285F4" 
            style="border:solid 1px #777" 
            width="800" 
            height="600" 
            frameborder="0" 
            scrolling="no">
    </iframe>
    '''
    st.markdown(calendar_html, unsafe_allow_html=True)

