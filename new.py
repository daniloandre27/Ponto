import fdb
import json
import streamlit as st
from datetime import datetime, time,timedelta
import time as tm
from fpdf import FPDF
from calendario import exibir_calendario, exibir_formulario_ferias,minhas_ferias_marcadas,ferias_marcadas,add_evento
import tempfile
import os
from PIL import Image
import base64
from io import BytesIO
import pandas as pd
import hashlib
#st.set_page_config(page_title="Sistema de Ponto")

def carregar_configuracao():
    try:
        with open('config.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        st.error("Arquivo de configuração 'config.json' não encontrado.")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Erro ao decodificar 'config.json': {e}")
        return None

# Configurações do banco de dados
DB_CONFIG = carregar_configuracao()

# Conexão persistente com o banco de dados
@st.cache_resource
def obter_conexao_persistente():
    if not DB_CONFIG:
        st.error("Configurações do banco não carregadas.")
        return None
    try:
        return fdb.connect(**DB_CONFIG)
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Reutilizar a conexão persistente
conexao_persistente = obter_conexao_persistente()

# Função para criptografar senhas
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Tela inicial
def tela_inicial():
    #st.markdown("<h1 style='text-align: center;'>Sistema de Registro de Ponto</h1>", unsafe_allow_html=True)
    if "usuario" not in st.session_state:
        tela_login()
    else:
        st.sidebar.image("logo-dna.png", use_container_width=True)
        usuario = st.session_state["usuario"]
        menu = ["Registrar Ponto"]
        menu.append("Agenda")
        menu.append("Visualizar Registros")
        menu.append("Minhas Horas Extras")
        menu.append("Minhas Férias")
        menu.append("Alterar Senha")
        if usuario.get("administrador"):
            menu.append("Cadastrar Funcionário")
            menu.append("Manutenção de Cadastro")
            menu.append("Agendamento")
            menu.append("Ferias Marcadas")
            menu.append("Banco de Horas")
            menu.append("Manutenção de Senha")
            menu.append("Agendar Ferias")
        menu.append("Sair")
        escolha = st.sidebar.selectbox("Opções", menu, label_visibility="hidden")
        if escolha == "Registrar Ponto":
            tela_funcionario()
        elif escolha == "Alterar Senha":
            alterar_senha()
        elif escolha == "Visualizar Registros":
            tela_periodo_trabalhado()
        elif escolha == "Agenda":
            exibir_calendario()
        elif escolha == "Minhas Horas Extras":
            tela_banco_horas()
        elif escolha == "Minhas Férias":
            minhas_ferias_marcadas()
        elif escolha == "Manutenção de Senha":
            tela_alterar_senha_admin()            
        elif escolha == "Cadastrar Funcionário" and usuario.get("administrador"):
            tela_administracao()
        elif escolha == "Manutenção de Cadastro"and usuario.get("administrador"):
            tela_manutencao_funcionarios()
        elif escolha == "Banco de Horas" and usuario.get("administrador"):
            tela_banco_horas_admin()
        elif escolha == "Ferias Marcadas" and usuario.get("administrador"):
            ferias_marcadas()
        elif escolha == "Agendamento" and usuario.get("administrador"):
            add_evento()
        elif escolha == "Agendar Ferias" and usuario.get("administrador"):
            exibir_formulario_ferias()
        elif escolha == "Cadastrar Funcionário":
            st.warning("Acesso restrito! Apenas administradores podem acessar.")
        elif escolha == "Sair":
            st.session_state.clear()
            st.success("Sessão encerrada!")
            st.rerun()

def tela_login():
    logo = "C:\\Users\\Jarvis\\Documents\\Projetos\\Ponto\\logo-dna.png"

    with open(logo, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
        <div style="display: flex; justify-content: center;margin-top: -20px;">
            <img src="data:image/png;base64,{base64_image}" style="width: 200px;"/>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<h1 style='text-align: center;'>Autenticação</h1>", unsafe_allow_html=True)

    with st.form(key="login_form"):
        username = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar",use_container_width = True)

        if submit_button:
            conn = conexao_persistente
            if conn:
                cursor = conexao_persistente.cursor()
                cursor.execute("""
                    SELECT id, nome, cargo, administrador, senha
                    FROM funcionarios
                    WHERE username = ?
                """, (username,))
                usuario = cursor.fetchone()

                if usuario:
                    # Verifica se o hash da senha fornecida corresponde ao armazenado
                    senha_hash = gerar_hash_senha(senha)  # Gera o hash da senha inserida
                    if usuario[4] == senha_hash:
                        st.session_state["usuario"] = {
                            "id": usuario[0],
                            "nome": usuario[1],
                            "cargo": usuario[2],
                            "administrador": bool(usuario[3])
                        }
                        st.success(f"Bem-vindo, {usuario[1]}!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.error("Usuário ou senha incorretos.")

@st.cache_data
def listar_usuarios():
    """Retorna todos os usuários cadastrados no banco."""
    if not conexao_persistente:
        st.error("Conexão com o banco de dados não disponível.")
        return []
    try:
        cursor = conexao_persistente.cursor()
        cursor.execute("SELECT ID, NOME, USERNAME FROM FUNCIONARIOS")
        usuarios = cursor.fetchall()
        return usuarios
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []


def alterar_senha_usuario(usuario_id, nova_senha):
    """Atualiza a senha do usuário no banco de dados."""
    senha_criptografada = criptografar_senha(nova_senha)
    cursor = conexao_persistente.cursor()
    cursor.execute("UPDATE FUNCIONARIOS SET SENHA = ? WHERE ID = ?", (senha_criptografada, usuario_id))
    conexao_persistente.commit()
    st.success("Senha alterada com sucesso!")

def tela_alterar_senha_admin():
    st.markdown("<h1 style='text-align: center;'>Alterar Senha de Usuários</h1>", unsafe_allow_html=True)

    usuarios = listar_usuarios()

    if not usuarios:
        st.warning("Nenhum usuário cadastrado encontrado.")
        return

    # Exibir a lista de usuários
    for usuario in usuarios:
        id_usuario, nome, username = usuario
        with st.expander(f"{nome} ({username})"):
            with st.form(key=f"form_usuario_{id_usuario}"):
                nova_senha = st.text_input("Digite a nova senha", type="password", key=f"senha_{id_usuario}")
                confirmar_senha = st.text_input("Confirme a nova senha", type="password", key=f"confirmar_{id_usuario}")
                alterar = st.form_submit_button("Alterar Senha")

                if alterar:
                    if not nova_senha or not confirmar_senha:
                        st.error("Por favor, preencha os dois campos de senha.")
                    elif nova_senha != confirmar_senha:
                        st.error("As senhas não coincidem. Tente novamente.")
                    else:
                        alterar_senha_usuario(id_usuario, nova_senha)


# Função para formatar horário
def formatar_horario(horario):
    """Formata o horário no formato HH:MM:SS ou retorna 'Não registrado' se nulo."""
    if horario is None:
        return ""

    if isinstance(horario, time):
        return horario.strftime("%H:%M:%S")

    if isinstance(horario, str):
        try:
            return datetime.strptime(horario, "%H:%M:%S").strftime("%H:%M:%S")
        except ValueError:
            return ""

    return "" #Removi a exibição do não registrado no frame

def obter_registros(funcionario_id, data_inicio, data_fim):
    """Obtém registros de ponto do banco de dados para o período selecionado."""
    conn = conexao_persistente  # Certifique-se de que essa função existe e retorna a conexão com o banco
    if not conn:
        st.error("Erro ao conectar ao banco de dados.")
        return None, None, None, pd.DataFrame()

    cursor = conexao_persistente.cursor()
    try:
        # Busca informações do funcionário
        cursor.execute("SELECT NOME, CARGO, DTCADASTRO FROM FUNCIONARIOS WHERE ID = ?", (funcionario_id,))
        funcionario = cursor.fetchone()

        if not funcionario:
            st.error("Funcionário não encontrado.")
            return None, None, None, pd.DataFrame()

        nome, cargo, dtcadastro = funcionario

        # Busca registros de ponto no período, garantindo que data_inicio e data_fim sejam respeitados
        cursor.execute("""
            SELECT DATA, CHEGADA, SAIDA_ALMOCO, RETORNO_ALMOCO, SAIDA 
            FROM REGISTROS 
            WHERE FUNCIONARIO_ID = ? AND DATA BETWEEN ? AND ?
            ORDER BY DATA
        """, (funcionario_id, data_inicio, data_fim))
        registros = cursor

        if not registros:
            st.warning("Nenhum registro encontrado no período selecionado.")
            return nome, cargo, dtcadastro, pd.DataFrame()

        # Formatar registros em um DataFrame
        df = pd.DataFrame(registros, columns=["Data", "Chegada", "Saída Almoço", "Retorno Almoço", "Saída"])

        # Garantir que a coluna 'Data' seja convertida para datetime e sem hora
        df["Data"] = pd.to_datetime(df["Data"]).dt.date  # Converte para apenas data (sem hora)

        # Criar a coluna "Dia da semana"
        dias_semana = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
        df["Dia"] = df["Data"].apply(lambda x: dias_semana[x.weekday()])

        # Criar a coluna "Data e Dia" no formato "dd/mm/yyyy - DDD"
        df["Data e Dia"] = df["Data"].apply(lambda x: x.strftime('%d/%m/%Y')) + " - " + df["Dia"]

        # Garantir que a coluna "Data e Dia" seja a primeira
        df = df[["Data e Dia", "Chegada", "Saída Almoço", "Retorno Almoço", "Saída"]]

        # Aplicar a formatação de horário
        df["Chegada"] = df["Chegada"].apply(formatar_horario)
        df["Saída Almoço"] = df["Saída Almoço"].apply(formatar_horario)
        df["Retorno Almoço"] = df["Retorno Almoço"].apply(formatar_horario)
        df["Saída"] = df["Saída"].apply(formatar_horario)

        # Adicionar dias faltantes no período solicitado
        todas_datas = pd.date_range(start=data_inicio, end=data_fim, freq='D')
        datas_existentes = df["Data e Dia"].to_list()

        # Dias que faltam no DataFrame (dentro do intervalo)
        dias_faltantes = [
            data.strftime("%d/%m/%Y") + " - " + dias_semana[data.weekday()] 
            for data in todas_datas 
            if data.strftime("%d/%m/%Y") + " - " + dias_semana[data.weekday()] not in datas_existentes
        ]
        
        # Criar um DataFrame com os dias faltantes
        dias_faltantes_df = pd.DataFrame(dias_faltantes, columns=["Data e Dia"])
        dias_faltantes_df["Chegada"] = ""
        dias_faltantes_df["Saída Almoço"] = ""
        dias_faltantes_df["Retorno Almoço"] = ""
        dias_faltantes_df["Saída"] = ""

        # Concatenar os dados existentes com os faltantes
        df = pd.concat([df, dias_faltantes_df], ignore_index=True)

        # Ordenar o DataFrame pela coluna "Data e Dia"
        df = df.sort_values(by="Data e Dia").reset_index(drop=True)

        # Centralizando os dados no dataframe
        df_style = df.style.set_properties(**{'text-align': 'center'})

        # Exibindo o dataframe centralizado
        #st.dataframe(df_style, use_container_width=True)
        st.dataframe(df,hide_index=True ,use_container_width=True)

        return nome, cargo, dtcadastro, df
    except Exception as e:
        st.error(f"Ocorreu um erro ao buscar os registros: {e}")
        return None, None, None, pd.DataFrame()
    finally:
        ''

# Função para gerar PDF
def gerar_pdf(nome, cargo, dtcadastro, df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=5)
    pdf.set_top_margin(0)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, "Relatório de Ponto", ln=True, align="C")

    # Informações da empresa e do funcionário lado a lado
    pdf.set_font("Arial", size=9)

    # Primeira coluna: informações da empresa (ajustada para ser mais larga)
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    pdf.multi_cell(100, 5, 
                   "Empresa: G2 E SA SOLUCOES EM INFORMATICA LTDA\n"
                   "CNPJ/CPF: 39.417.670/0001-43\n"
                   "Endereço: GETULIO VARGAS\n"
                   "Cidade/UF: SANTO ANTONIO DE PADUA - RJ", 
                   border=1)
    
    # Segunda coluna: informações do funcionário (texto alinhado à direita)
    pdf.set_xy(x_start + 100, y_start)  # Move para a próxima coluna
    pdf.multi_cell(90, 5, 
                   f"136 - {nome}\n"
                   f"Função: 007 - {cargo}\n"
                   f"Admissão: {dtcadastro.strftime('%d/%m/%Y')}\n"
                   f"Horário: 08:00 - 11:00 - 12:00 - 17:00", 
                   border=1, align="R")
    #pdf.ln(10)

    pdf.set_font("Arial", style="B", size=9)
    pdf.cell(34, 7, "Dia", 1, 0, "C")
    pdf.cell(39, 7, "Chegada", 1, 0, "C")
    pdf.cell(39, 7, "Saída Almoço", 1, 0, "C")
    pdf.cell(39, 7, "Retorno Almoço", 1, 0, "C")
    pdf.cell(39, 7, "Saída", 1, 1, "C")

    # Dados da tabela
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        # Garantir que a "Data e Dia" seja uma string válida
        data_dia = str(row["Data e Dia"]) if pd.notnull(row["Data e Dia"]) else ""

        # Preencher as células, convertendo valores para string quando necessário
        pdf.cell(34, 6, data_dia, 1, 0, "L")
        pdf.cell(39, 6, str(row["Chegada"]), 1, 0, "C")
        pdf.cell(39, 6, str(row["Saída Almoço"]), 1, 0, "C")
        pdf.cell(39, 6, str(row["Retorno Almoço"]), 1, 0, "C")
        pdf.cell(39, 6, str(row["Saída"]), 1, 1, "C")
    
    # Adicionar as assinaturas e a data
    pdf.ln(8)
    pdf.set_font("Arial", size=9)

    # Reconhecimento e Data
    pdf.cell(0, 10, "Reconheço a exatidão destas anotações.", ln=True, align="L")
    pdf.cell(30, 10, "Data: ____/____/____", 0, 0, "L")
    pdf.ln(10)

    largura_pagina = pdf.w - 2 * pdf.l_margin
    largura_assinatura = largura_pagina / 2  # Metade da largura para cada assinatura

    # Assinatura do Funcionário (centralizado na metade esquerda)
    pdf.cell(largura_assinatura, 8, "______________________________________", 0, 0, "C")

    # Assinatura do Diretor (centralizado na metade direita)
    pdf.cell(largura_assinatura, 8, "______________________________________", 0, 1, "C")
    pdf.set_y(pdf.get_y() - 2)
    # Legendas das assinaturas
    pdf.cell(largura_assinatura, 8, "Ass. Funcionário", 0, 0, "C")
    pdf.cell(largura_assinatura, 8, "Ass. do Diretor", 0, 1, "C")

    # Criar um arquivo temporário para salvar o PDF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)

    return temp_file.name  # Retorna o caminho do arquivo temporário




# Função principal para exibição do relatório
def tela_periodo_trabalhado():
    """Tela principal para exibição do relatório de ponto."""
    if "usuario" not in st.session_state:
        st.warning("Faça login para acessar esta área.")
        return

    usuario = st.session_state["usuario"]

    #st.title("Relatório de Ponto")
    st.markdown("<h1 style='text-align: center;'>Relatório de Ponto</h1>", unsafe_allow_html=True)
    st.write("Selecione o período desejado para exibir os registros de ponto:")

    # Seleção de período
    col1, col2 = st.columns(2)
    with col1:
        primeiro_dia_mes = datetime(datetime.now().year, datetime.now().month, 1)
        data_inicio = st.date_input("Data de início", value=primeiro_dia_mes,format="DD/MM/YYYY")
        #st.write("Data selecionada:", data_inicio.strftime("%d/%m/%Y"))
        #data_inicio = st.date_input("Data de início", value=datetime.now() - timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data de fim", value=datetime.now(),format="DD/MM/YYYY")

    if data_inicio > data_fim:
        st.error("A data de início não pode ser maior que a data de fim.")
        return

    funcionario_id = usuario.get("id")
    if not funcionario_id:
        st.error("Erro ao identificar o funcionário logado.")
        return

    # Obter registros
    nome, cargo, dtcadastro, df = obter_registros(funcionario_id, data_inicio, data_fim)

    if not df.empty:
        #st.dataframe(df)

        # Gerar PDF e oferecer download
        pdf_file = gerar_pdf(nome, cargo, dtcadastro, df)
        with open(pdf_file, "rb") as f:
            st.download_button(
                label="Baixar Relatório em PDF",
                data=f,
                file_name=f"Relatorio_Ponto_{nome.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
        os.remove(pdf_file)  # Remover arquivo temporário
    else:
        st.warning("Nenhum registro encontrado no período selecionado.")

def tela_funcionario():
    if "usuario" not in st.session_state:
        st.warning("Faça login para acessar esta área.")
        return

    usuario = st.session_state["usuario"]

    # Supondo que usuario['nome'] contenha o nome completo
    nome_completo = usuario['nome']
    primeiro_nome, primeiro_sobrenome = nome_completo.split()[:2]

    # Exibir no Streamlit
    st.markdown(
        f"<h1 style='text-align: center;font-size: 40px;'>Olá, {primeiro_nome} {primeiro_sobrenome}!</h1>", 
        unsafe_allow_html=True
    )
    
    #st.markdown(f"<h1 style='text-align: center;'>Olá, {usuario['nome']}!</h1>", unsafe_allow_html=True)
    st.write('______________________________________________')

    def registrar_ponto(tipo, cursor):
        data_atual = datetime.now().date()
        hora_atual = datetime.now().time()

        # Verificar se o ponto já foi registrado
        cursor.execute(f"""
            SELECT {tipo}
            FROM REGISTROS
            WHERE FUNCIONARIO_ID = ? AND DATA = ?
        """, (usuario["id"], data_atual))
        registro = cursor.fetchone()

        placeholder = st.empty()  # Espaço reservado para a mensagem
        if registro and registro[0]:
            placeholder = st.empty() 
            placeholder.warning(f"Já registrado!", icon="⚠️")
            tm.sleep(1)
            placeholder.empty()
        else:
            cursor.execute(f"""
                UPDATE OR INSERT INTO REGISTROS (FUNCIONARIO_ID, DATA, {tipo})
                VALUES (?, ?, ?)
                MATCHING (FUNCIONARIO_ID, DATA)
            """, (usuario["id"], data_atual, hora_atual))

            # Processar horas extras se for a saída
            if tipo == "SAIDA":
                cursor.execute("""
                    SELECT CHEGADA, SAIDA_ALMOCO, RETORNO_ALMOCO, SAIDA
                    FROM REGISTROS
                    WHERE FUNCIONARIO_ID = ? AND DATA = ?
                """, (usuario["id"], data_atual))
                registros = cursor.fetchone()

                if registros and registros[0] and registros[3]:
                    calcular_horas_extras(cursor, registros, data_atual, usuario["id"])

            conn.commit()
            placeholder = st.empty() 
            placeholder.success(f"Registrado!", icon="✅")
            tm.sleep(1)
            placeholder.empty()

    def calcular_horas_extras(cursor, registros, data_atual, funcionario_id):
        chegada = datetime.combine(data_atual, registros[0])
        saida = datetime.combine(data_atual, registros[3])
        intervalo_almoco = timedelta()

        if registros[1] and registros[2]:  # Verificar se há almoço registrado
            intervalo_almoco = datetime.combine(data_atual, registros[2]) - datetime.combine(data_atual, registros[1])

        total_horas = saida - chegada - intervalo_almoco
        limite_horas = timedelta(hours=8, minutes=40)

        if total_horas > limite_horas:
            horas_extras = total_horas - limite_horas
            # Formatando horas extras para "HH:MM:SS"
            horas_extras_time = f"{horas_extras.seconds // 3600:02}:{(horas_extras.seconds // 60) % 60:02}:{horas_extras.seconds % 60:02}"
            cursor.execute("""
                UPDATE REGISTROS
                SET HORAEXTRA = ?
                WHERE FUNCIONARIO_ID = ? AND DATA = ?
            """, (horas_extras_time, funcionario_id, data_atual))


    # Criar uma conexão persistente
    conn = conexao_persistente
    if conn:
        cursor = conexao_persistente.cursor()

        # Botões para registrar pontos
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Chegada", use_container_width=True):
                registrar_ponto("CHEGADA", cursor)
        with col2:
            if st.button("Saída Almoço", use_container_width=True):
                registrar_ponto("SAIDA_ALMOCO", cursor)
        with col3:
            if st.button("Retorno Almoço", use_container_width=True):
                registrar_ponto("RETORNO_ALMOCO", cursor)
        with col4:
            if st.button("Saída", use_container_width=True):
                registrar_ponto("SAIDA", cursor)
    #st.write('______________________________________________')
    #st.divider()
    #st.markdown("""<hr style="height:10px;border:none;color:#333;background-color:#333;" /> """, unsafe_allow_html=True)

    conn = conexao_persistente
    if conn:
        cursor = conexao_persistente.cursor()
        data_atual = datetime.now().date()

        cursor.execute("""
            SELECT CHEGADA, SAIDA_ALMOCO, RETORNO_ALMOCO, SAIDA
            FROM REGISTROS
            WHERE FUNCIONARIO_ID = ? AND DATA = ?
        """, (usuario["id"], data_atual))
        registros = cursor.fetchone()

    if registros:
        #st.markdown("<h1 style='text-align: center;'>Registros de Hoje:</h1>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 40px;'>Registros de Hoje:</h1>", unsafe_allow_html=True)
        data_atual = datetime.now().strftime("%Y-%m-%d")
        df = pd.DataFrame([registros] ,columns=["Chegada", "Saída Almoço", "Retorno Almoço", "Saída"])
        df = df.fillna("Não registrado")

        for col in ["Chegada", "Saída Almoço", "Retorno Almoço", "Saída"]:
            df[col] = df[col].apply(
                lambda x: pd.to_datetime(f"{data_atual} {x}", errors='coerce').strftime("%H:%M:%S") 
                if x != "Não registrado" else x
            )

        #df.set_index("Chegada", inplace=True)    
        #st.dataframe(df, use_container_width=True,)
        st.dataframe(df,hide_index=True ,use_container_width=True)
        if registros[0] != "Não registrado":
            # Formatar a hora de chegada para datetime
            hora_chegada = pd.to_datetime(f"{data_atual} {registros[0]}")

            # Se a hora de saída não estiver registrada ou for inválida, usa a hora atual
            if registros[3] != "Não registrado" and registros[3]:
                try:
                    hora_saida = pd.to_datetime(f"{data_atual} {registros[3]}")
                except Exception as e:
                    st.warning(f"Erro ao processar a hora de saída: {e}. Usando hora atual.")
                    hora_saida = datetime.now()
            else:
                hora_saida = datetime.now()

            # Calcular a diferença
            total_horas = hora_saida - hora_chegada

            # Formatando para exibir apenas HH:mm:ss, mesmo que ultrapasse 24 horas
            total_segundos = int(total_horas.total_seconds())
            horas, resto = divmod(total_segundos, 3600)
            minutos, segundos = divmod(resto, 60)
            total_horas_formatado = f"{horas:02}:{minutos:02}:{segundos:02}"

            st.markdown(f"**Total de horas trabalhadas:** {total_horas_formatado}")
        else:
            st.warning("Chegada não registrada para calcular as horas trabalhadas.")


def tela_banco_horas():
    usuario = st.session_state["usuario"]
    st.title("Banco de Horas")

    conn = conexao_persistente
    if conn:
        cursor = conexao_persistente.cursor()
        try:
            # Consulta ajustada para excluir valores nulos
            cursor.execute("""
                SELECT DATA, HORAEXTRA
                FROM REGISTROS
                WHERE FUNCIONARIO_ID = ? AND HORAEXTRA IS NOT NULL
                ORDER BY DATA
            """, (usuario["id"],))
            registros = cursor.fetchall()

            if registros:
                # Criando o DataFrame
                df = pd.DataFrame(registros, columns=["Data", "Hora Extra"])

                # Convertendo 'Data' para datetime e formatando como 'dd/mm/yyyy'
                df["Data"] = pd.to_datetime(df["Data"]).dt.strftime("%d/%m/%Y")

                # Convertendo 'Hora Extra' para string no formato 'HH:MM:SS'
                def format_hora_extra(time_value):
                    if isinstance(time_value, str):  # Caso já seja string no formato "HH:MM:SS"
                        return time_value
                    elif isinstance(time_value, time):  # Caso seja um objeto time
                        return time_value.strftime("%H:%M:%S")
                    else:
                        st.warning(f"Valor inesperado em Hora Extra: {time_value}")
                        return "00:00:00"

                df["Hora Extra"] = df["Hora Extra"].apply(format_hora_extra)

                # Definindo a coluna 'Data' como índice
                #df.set_index("Data", inplace=True)

                st.dataframe(df,hide_index=True ,use_container_width=True)

                # Calculando o total de horas extras
                total_horas = timedelta()
                for hora in df["Hora Extra"]:
                    h, m, s = map(int, hora.split(":"))
                    total_horas += timedelta(hours=h, minutes=m, seconds=s)

                total_horas_em_horas = total_horas.total_seconds() / 3600 if total_horas else 0

                # Calculando dias adicionais (1 dia = 10 horas)
                dias_adicionais = int(total_horas_em_horas // 10)
                horas_restantes = total_horas_em_horas % 10

                # Calculando os minutos restantes após a parte das horas
                minutos_restantes = (total_horas.total_seconds() % 3600) / 60

                # Exibindo horas extras como "X Dia(s) e HH:MM"
                if total_horas_em_horas >= 10:
                    horas_extras_display = f"{dias_adicionais} Dia(s) e {int(horas_restantes):02d}:{int(minutos_restantes):02d}"
                else:
                    horas_extras_display = f"{int(horas_restantes):02d}:{int(minutos_restantes):02d}"

                # Exibindo resultados
                st.markdown(f"**Horas Extras:** {horas_extras_display}")
            else:
                st.warning("Você não tem horas extras!")
        except Exception as e:
            st.error(f"Erro ao executar a consulta: {e}")
    else:
        st.error("Não foi possível conectar ao banco de dados.")


def tela_banco_horas_admin():
    st.title("Banco de Horas - Administração")

    conn = conexao_persistente
    if conn:
        cursor = conexao_persistente.cursor()
        try:
            # Consulta para buscar todas as horas extras com nome do funcionário
            cursor.execute("""
                SELECT f.NOME AS Funcionario, r.DATA AS Data, r.HORAEXTRA AS HoraExtra
                FROM REGISTROS r
                JOIN FUNCIONARIOS f ON r.FUNCIONARIO_ID = f.ID
                WHERE r.HORAEXTRA IS NOT NULL
                ORDER BY f.NOME, r.DATA
            """)
            registros = cursor.fetchall()

            if registros:
                # Criando o DataFrame para exibir detalhes diários
                df_detalhes = pd.DataFrame(registros, columns=["Funcionário", "Data", "Hora Extra"])

                # Convertendo 'Data' para datetime e formatando como 'dd/mm/yyyy'
                df_detalhes["Data"] = pd.to_datetime(df_detalhes["Data"]).dt.strftime("%d/%m/%Y")

                # Convertendo 'Hora Extra' para string no formato 'HH:MM:SS'
                def format_hora_extra(time_value):
                    if isinstance(time_value, str):
                        return time_value
                    elif isinstance(time_value, time):
                        return time_value.strftime("%H:%M:%S")
                    else:
                        return "00:00:00"

                df_detalhes["Hora Extra"] = df_detalhes["Hora Extra"].apply(format_hora_extra)

                # Filtro para selecionar um funcionário específico
                funcionarios_unicos = df_detalhes["Funcionário"].unique()
                funcionario_selecionado = st.selectbox("Selecione um Funcionário", options=funcionarios_unicos)

                # Filtrando o DataFrame com base no funcionário selecionado
                df_filtrado = df_detalhes[df_detalhes["Funcionário"] == funcionario_selecionado]

                # Definindo a coluna 'Funcionário' como índice
                #df_filtrado.set_index("Funcionário", inplace=True)

                # Exibindo o DataFrame filtrado de detalhes
                st.subheader("Detalhes por Dia")
                st.dataframe(df_filtrado, use_container_width=True,hide_index=True)

                # Criando o DataFrame para exibir totais por funcionário
                total_horas_por_funcionario = {}

                for _, row in df_detalhes.iterrows():
                    funcionario = row["Funcionário"]
                    h, m, s = map(int, row["Hora Extra"].split(":"))
                    horas_extras = timedelta(hours=h, minutes=m, seconds=s)

                    if funcionario in total_horas_por_funcionario:
                        total_horas_por_funcionario[funcionario] += horas_extras
                    else:
                        total_horas_por_funcionario[funcionario] = horas_extras

                # Preparando o DataFrame de totais
                totais_data = []
                for funcionario, total_timedelta in total_horas_por_funcionario.items():
                    total_horas = total_timedelta.total_seconds() / 3600

                    dias_adicionais = int(total_horas // 10)
                    horas_restantes = int(total_horas % 10)
                    minutos_restantes = int((total_timedelta.total_seconds() % 3600) / 60)

                    total_formatado = f"{dias_adicionais} Dia(s) e {horas_restantes:02d}:{minutos_restantes:02d}"
                    totais_data.append([funcionario, total_formatado])

                df_totais = pd.DataFrame(totais_data, columns=["Funcionário", "Total de Horas Extras"])

                # Definindo a coluna 'Funcionário' como índice
                #df_totais.set_index("Funcionário", inplace=True)

                # Exibindo o DataFrame de totais
                st.subheader("Totais por Funcionário")
                st.dataframe(df_totais, use_container_width=True,hide_index=True)
            else:
                st.warning("Nenhum registro de horas extras encontrado.")
        except Exception as e:
            st.error(f"Erro ao executar a consulta: {e}")
    else:
        st.error("Não foi possível conectar ao banco de dados.")


# Função para gerar o hash de uma senha
def gerar_hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Função para alterar a senha
def alterar_senha():
    st.markdown("<h1 style='text-align: center;'>Alteração de Senha</h1>", unsafe_allow_html=True)

    if "usuario" not in st.session_state:
        st.warning("Faça login para acessar esta área.")
        return

    usuario = st.session_state["usuario"]
    with st.form(key="alterar_senha_form"):
        senha_atual = st.text_input("Senha Atual", type="password")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
        submit_button = st.form_submit_button("Alterar Senha")

        if submit_button:
            if not senha_atual or not nova_senha or not confirmar_senha:
                st.error("Por favor, preencha todos os campos.")
                return

            if nova_senha != confirmar_senha:
                st.error("A nova senha e a confirmação não coincidem.")
                return

            conn = conexao_persistente
            if conn:
                cursor = conexao_persistente.cursor()

                # Verificar se a senha atual está correta
                cursor.execute("""
                    SELECT senha
                    FROM funcionarios
                    WHERE id = ?
                """, (usuario["id"],))
                registro = cursor.fetchone()

                if not registro or registro[0] != gerar_hash_senha(senha_atual):
                    st.error("Senha atual incorreta.")
                else:
                    # Atualizar a senha no banco de dados
                    nova_senha_hash = gerar_hash_senha(nova_senha)
                    cursor.execute("""
                        UPDATE funcionarios
                        SET senha = ?
                        WHERE id = ?
                    """, (nova_senha_hash, usuario["id"]))
                    conn.commit()
                    st.success("Senha alterada com sucesso!")
            else:
                st.error("Erro ao conectar ao banco de dados.")

def tela_manutencao_funcionarios():
    st.markdown("<h1 style='text-align: center;'>Manutenção de Funcionários</h1>", unsafe_allow_html=True)
    
    # Listar os usuários cadastrados
    usuarios = listar_usuarios()
    if not usuarios:
        st.warning("Nenhum funcionário encontrado.")
        return

    # Criar um DataFrame para facilitar o filtro
    df_usuarios = pd.DataFrame(usuarios, columns=["ID", "Nome", "Username"])

    # Dropdown para selecionar o funcionário
    funcionarios_unicos = df_usuarios["Nome"].unique()
    funcionario_selecionado = st.selectbox("Selecione um Funcionário", options=funcionarios_unicos)

    # Filtrar os dados do funcionário selecionado
    df_filtrado = df_usuarios[df_usuarios["Nome"] == funcionario_selecionado]
    if df_filtrado.empty:
        st.warning("Funcionário não encontrado.")
        return

    # Obter os dados do funcionário selecionado
    funcionario = df_filtrado.iloc[0]
    id_usuario = funcionario["ID"]
    nome_atual = funcionario["Nome"]
    username = funcionario["Username"]

    with st.expander(f"Editar dados de {nome_atual} ({username})"):
        with st.form(f"form_editar_usuario_{id_usuario}"):
            novo_nome = st.text_input("Nome do Funcionário", value=nome_atual)
            novo_cargo = st.text_input("Cargo do Funcionário")  # Cargo pode ser carregado do banco se disponível
            administrador = st.checkbox("Administrador", value=False)  # Atualizar com a flag correta se disponível

            # Alterar senha com validação
            st.markdown("### Alterar Senha (opcional)")
            alterar_senha = st.selectbox(
                "Deseja alterar a senha?",
                options=["Não", "Sim"]
            )
            if alterar_senha == "Sim":
                nova_senha = st.text_input("Digite a nova senha", type="password")
                confirmar_senha = st.text_input("Confirme a nova senha", type="password")
                if nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
            
            submit_button = st.form_submit_button("Salvar Alterações")

            if submit_button:
                conn = conexao_persistente
                if conn:
                    cursor = conexao_persistente.cursor()
                    try:
                        # Atualizar nome, cargo e status de administrador
                        cursor.execute("""
                            UPDATE funcionarios 
                            SET nome = ?, cargo = ?, administrador = ? 
                            WHERE id = ?
                        """, (novo_nome, novo_cargo, administrador, id_usuario))

                        # Atualizar senha somente se a opção for escolhida e as senhas forem válidas
                        if alterar_senha == "Sim" and nova_senha == confirmar_senha:
                            senha_criptografada = criptografar_senha(nova_senha)
                            cursor.execute("""
                                UPDATE funcionarios 
                                SET senha = ? 
                                WHERE id = ?
                            """, (senha_criptografada, id_usuario))

                        conn.commit()
                        st.success(f"Dados do funcionário {novo_nome} atualizados com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao atualizar os dados do funcionário: {e}")
                    finally:
                        ''

# Tela de administração
def tela_administracao():
    st.markdown("<h1 style='text-align: center;'>Cadastrar Funcionário</h1>", unsafe_allow_html=True)
    with st.form("form_cadastro"):
        nome = st.text_input("Nome do Funcionário")
        username = st.text_input("Nome de Usuário")
        senha = st.text_input("Senha", type="password")
        cargo = st.text_input("Cargo")
        administrador = st.checkbox("Conceder acesso administrativo")
        submit_button = st.form_submit_button("Cadastrar")

        if submit_button:
            conn = conexao_persistente()
            if conn:
                cursor = conexao_persistente.cursor()
                senha_criptografada = criptografar_senha(senha)
                try:
                    cursor.execute("""
                        INSERT INTO funcionarios (nome, username, senha, cargo, administrador)
                        VALUES (?, ?, ?, ?, ?)
                    """, (nome, username, senha_criptografada, cargo, administrador))
                    conn.commit()
                    st.success(f"Funcionário {nome} cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao cadastrar funcionário: {e}")

# Iniciar o aplicativo
if __name__ == "__main__":
    st.set_page_config(page_title="Sistema de Ponto")
    tela_inicial()