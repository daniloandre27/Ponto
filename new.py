import streamlit as st
import psycopg2
import json
import re
from pathlib import Path
from datetime import datetime, time,timedelta
import time as tm
from fpdf import FPDF
#from calendario import exibir_calendario, exibir_formulario_ferias,minhas_ferias_marcadas,ferias_marcadas,add_evento
import tempfile
import os
import base64
import pandas as pd
import hashlib
from io import BytesIO
from zipfile import ZipFile
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
st.set_page_config(page_title="Sistema de Ponto", layout="centered")
# 🔹 Função para carregar as configurações do banco de dados

DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "database": st.secrets["DB_NAME"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASS"],
    "port": st.secrets["DB_PORT"]
}

@st.cache_resource
def obter_conexao_persistente():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"]
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Criar conexão
conexao_persistente = obter_conexao_persistente()


# Função para criptografar senhas
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Tela inicial

import streamlit as st

def tela_inicial():
    if "usuario" not in st.session_state:
        tela_login()
    else:
        # 🔹 Sidebar sempre visível
        st.sidebar.image("logo-dna.png", use_container_width=True)
        usuario = st.session_state["usuario"]

        # 🔹 Definir "Registrar Ponto" como a tela inicial automaticamente após login
        if "menu_ativo" not in st.session_state:
            st.session_state.menu_ativo = "Registrar Ponto"  # 🔥 Tela inicial

        # 🔹 Resetar os menus ao trocar de seleção
        def resetar_menus(exceto=None):
            """Reseta os menus, exceto o que foi selecionado"""
            if exceto != "geral":
                st.session_state.menu_geral = None
            if exceto != "admin":
                st.session_state.menu_admin = None
            if exceto != "agenda":
                st.session_state.menu_agenda = None
            if exceto != "edita_ponto":
                st.session_state.menu_edita_ponto = None

        # 🔹 Menu Geral (Agora recolhido por padrão)
        with st.sidebar.expander("📌 Menu Geral", expanded=False):  # 🔽 Fica recolhido por padrão
            escolha_geral = st.radio(
                "Opções Gerais", 
                ["Registrar Ponto", "Agenda", "Meus Registros", "Minhas Faltas",
                 "Minhas Horas Extras", "Minhas Férias", "Alterar Senha"], 
                index=None,  
                key="menu_geral",
                on_change=resetar_menus, 
                args=("geral",)
            )

        # 🔹 Menu Administração (Recolhido por padrão)
        escolha_admin = None
        if usuario.get("administrador"):
            with st.sidebar.expander("🔧 Administração", expanded=False):  # 🔽 Fica recolhido por padrão
                escolha_admin = st.radio(
                    "Opções Administrativas",
                    ["Cadastrar Funcionário", "Alterar Cadastro", "Manutenção de Senha",
                     "Banco de Horas", "Registro de Faltas", "Registros do Ponto"],
                    index=None,  
                    key="menu_admin",
                    on_change=resetar_menus, 
                    args=("admin",)
                )

        # 🔹 Menu Agenda (Recolhido por padrão)
        escolha_agenda = None
        if usuario.get("agendamento"):
            with st.sidebar.expander("📅 Agenda", expanded=False):  # 🔽 Fica recolhido por padrão
                escolha_agenda = st.radio(
                    "Opções de Agenda",
                    ["Agendar Férias", "Férias Marcadas", "Agendamento"],
                    index=None,  
                    key="menu_agenda",
                    on_change=resetar_menus, 
                    args=("agenda",)
                )

        # 🔹 Menu Gerência/Ponto (Recolhido por padrão)
        escolha_editar_ponto = None
        if usuario.get("edita_ponto"):
            with st.sidebar.expander("🕒 Gerenciamento de Ponto", expanded=False):  # 🔽 Fica recolhido por padrão
                escolha_editar_ponto = st.radio(
                    "Gerência",
                    ["Manutenção do Ponto"],
                    index=None,  
                    key="menu_edita_ponto",
                    on_change=resetar_menus, 
                    args=("edita_ponto",)
                )

        # 🔹 Atualizar estado da sessão com base na escolha ativa
        escolha = escolha_geral or escolha_admin or escolha_agenda or escolha_editar_ponto
        if escolha:
            st.session_state.menu_ativo = escolha  # Armazena a escolha ativa no session_state

        # 🔹 Exibir apenas UMA TELA por vez (conforme a escolha ativa)
        if st.session_state.menu_ativo == "Registrar Ponto":
            tela_funcionario()
        elif st.session_state.menu_ativo == "Alterar Senha":
            alterar_senha()
        elif st.session_state.menu_ativo == "Agenda":
            exibir_calendario()
        elif st.session_state.menu_ativo == "Meus Registros":
            tela_periodo_trabalhado()
        elif st.session_state.menu_ativo == "Minhas Faltas":
            tela_usuario_faltas()
        elif st.session_state.menu_ativo == "Minhas Horas Extras":
            tela_banco_horas()
        elif st.session_state.menu_ativo == "Minhas Férias":
            minhas_ferias_marcadas()

        elif st.session_state.menu_ativo == "Cadastrar Funcionário":
            tela_administracao()
        elif st.session_state.menu_ativo == "Alterar Cadastro":
            tela_manutencao_funcionarios()
        elif st.session_state.menu_ativo == "Registros do Ponto":
            tela_periodo_trabalhado_adm()
        elif st.session_state.menu_ativo == "Manutenção do Ponto":
            tela_registro_ponto_manual()
        elif st.session_state.menu_ativo == "Banco de Horas":
            tela_banco_horas_admin()
        elif st.session_state.menu_ativo == "Registro de Faltas":
            tela_admin_faltas()
        elif st.session_state.menu_ativo == "Manutenção de Senha":
            tela_alterar_senha_admin()

        elif st.session_state.menu_ativo == "Agendar Férias":
            exibir_formulario_ferias()
        elif st.session_state.menu_ativo == "Férias Marcadas":
            ferias_marcadas()
        elif st.session_state.menu_ativo == "Agendamento":
            add_evento()

        # 🔹 Botão de saída SEMPRE visível no sidebar
        if st.sidebar.button("Sair", use_container_width=True):
            st.session_state.clear()
            st.sidebar.success("Sessão encerrada!")
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
            username = username.strip()
            if conn:
                cursor = conexao_persistente.cursor()
                cursor.execute("""
                    SELECT id, nome, cargo, administrador, agendamento,edita_ponto, senha
                    FROM funcionarios
                    WHERE username = %s
                """, (username,))

                usuario = cursor.fetchone()

                if usuario:
                    # Verifica se o hash da senha fornecida corresponde ao armazenado
                    senha_hash = gerar_hash_senha(senha)  # Gera o hash da senha inserida
                    if usuario[6] == senha_hash:
                        st.session_state["usuario"] = {
                            "id": usuario[0],
                            "nome": usuario[1],
                            "cargo": usuario[2],
                            "administrador": usuario[3] == '1',
                            "agendamento": usuario[4] == '1',
                            "edita_ponto": usuario[5] == '1',
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
        cursor.execute("""SELECT ID, NOME, USERNAME, EMAIL, DTCONTRATACAO, ADMINISTRADOR, AGENDAMENTO, EDITA_PONTO FROM FUNCIONARIOS ORDER BY 2""")
        usuarios = cursor.fetchall()
        return usuarios
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []



def alterar_senha_usuario(usuario_id, nova_senha):
    """Atualiza a senha do usuário no banco de dados."""
    senha_criptografada = criptografar_senha(nova_senha)
    cursor = conexao_persistente.cursor()
    cursor.execute("UPDATE FUNCIONARIOS SET SENHA = %s WHERE ID = %s", (senha_criptografada, usuario_id))
    conexao_persistente.commit()
    st.success("Senha alterada com sucesso!")


def tela_alterar_senha_admin():
    st.markdown("<h1 style='text-align: center;'>Alterar Senha de Usuários</h1>", unsafe_allow_html=True)

    usuarios = listar_usuarios()

    if not usuarios:
        st.warning("Nenhum usuário cadastrado encontrado.")
        return

    # Criar um DataFrame para facilitar o uso
    df_usuarios = pd.DataFrame(usuarios, columns=["ID", "Nome", "Username", "Email", "DtContratacao", "Administrador", "Agendamento","edita_ponto"])

    # Selectbox para escolher o usuário
    nomes_usuarios = df_usuarios["Nome"].tolist()
    usuario_selecionado = st.selectbox("Selecione um usuário para alterar a senha", options=nomes_usuarios)

    # Obter o ID do usuário selecionado
    usuario_info = df_usuarios[df_usuarios["Nome"] == usuario_selecionado].iloc[0]
    id_usuario = usuario_info["ID"]

    # Formulário para alterar a senha
    with st.form(key=f"form_usuario_{id_usuario}"):
        nova_senha = st.text_input("Digite a nova senha", type="password", key=f"senha_{id_usuario}")
        confirmar_senha = st.text_input("Confirme a nova senha", type="password", key=f"confirmar_{id_usuario}")
        alterar = st.form_submit_button("Alterar Senha", use_container_width=True)

        if alterar:
            if not nova_senha or not confirmar_senha:
                st.error("Por favor, preencha os dois campos de senha.")
            elif nova_senha != confirmar_senha:
                st.error("As senhas não coincidem. Tente novamente.")
            else:
                try:
                    alterar_senha_usuario(id_usuario, nova_senha)
                    st.success(f"Senha do usuário {usuario_selecionado} alterada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao alterar a senha: {e}")



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
        cursor.execute("SELECT NOME, CARGO, DTCADASTRO FROM FUNCIONARIOS WHERE ID = %s", (funcionario_id,))
        funcionario = cursor.fetchone()

        if not funcionario:
            st.error("Funcionário não encontrado.")
            return None, None, None, pd.DataFrame()

        nome, cargo, dtcadastro = funcionario

        # Busca registros de ponto no período, garantindo que data_inicio e data_fim sejam respeitados
        cursor.execute("""
            SELECT DATA, CHEGADA, SAIDA_ALMOCO, RETORNO_ALMOCO, SAIDA 
            FROM REGISTROS 
            WHERE FUNCIONARIO_ID = %s AND DATA BETWEEN %s AND %s
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
#Cadastro da empresa
def carregar_dados_empresa():
    caminho_arquivo = Path("empresa.json")
    if not caminho_arquivo.exists():
        raise FileNotFoundError("O arquivo 'empresa.json' não foi encontrado na raiz do projeto.")
    
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)

# Função para gerar PDF
def gerar_pdf(nome, cargo, dtcadastro, df):

    # Carregar informações da empresa do arquivo JSON
    try:
        dados_empresa = carregar_dados_empresa()
    except FileNotFoundError as e:
        print(e)
        return
        
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
                    f"Empresa: {dados_empresa['nome']}\n"
                    f"CNPJ/CPF: {dados_empresa['cnpj']}\n"
                    f"Endereço: {dados_empresa['endereco']}\n"
                    f"Cidade/UF: {dados_empresa['cidade']} - {dados_empresa['uf']}",                   
                   border=1)
    
    # Segunda coluna: informações do funcionário (texto alinhado à direita)
    pdf.set_xy(x_start + 100, y_start)  # Move para a próxima coluna
    pdf.multi_cell(90, 5, 
                   f"136 - {nome}\n"
                   f"Função: 007 - {cargo}\n"
                   f"Admissão: {dtcadastro.strftime('%d/%m/%Y') if dtcadastro else 'Não informado'}\n"
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

###
##
def tela_periodo_trabalhado_adm():
    """Tela principal para exibição do relatório de ponto."""
    if "usuario" not in st.session_state:
        st.warning("Faça login para acessar esta área.")
        return

    # Conexão com o banco de dados
    conn = conexao_persistente
    if not conn:
        st.error("Erro ao conectar ao banco de dados.")
        return

    cursor = conn.cursor()
    cursor.execute("ROLLBACK")

    # Título e instruções
    st.markdown("<h1 style='text-align: center;'>Relatório de Ponto</h1>", unsafe_allow_html=True)
    st.write("Selecione o período desejado para exibir os registros de ponto:")


    # Obter lista de funcionários
    cursor.execute("SELECT ID, NOME FROM FUNCIONARIOS ORDER BY NOME")
    funcionarios = cursor.fetchall()
    opcoes_funcionarios = {f"{nome}": id_func for id_func, nome in funcionarios}

    # Seleção do funcionário
    funcionario_selecionado = st.selectbox("Selecione o Funcionário:", options=opcoes_funcionarios.keys())

    if not funcionario_selecionado:
        st.warning("Selecione um funcionário para continuar.")
        return

    funcionario_id = opcoes_funcionarios[funcionario_selecionado]

    # Seleção de período
    col1, col2 = st.columns(2)
    with col1:
        primeiro_dia_mes = datetime(datetime.now().year, datetime.now().month, 1)
        data_inicio = st.date_input("Data de início", value=primeiro_dia_mes, format="DD/MM/YYYY")
    with col2:
        data_fim = st.date_input("Data de fim", value=datetime.now(), format="DD/MM/YYYY")

    if data_inicio > data_fim:
        st.error("A data de início não pode ser maior que a data de fim.")
        return

    # Obter registros do funcionário selecionado
    nome, cargo, dtcadastro, df = obter_registros(funcionario_id, data_inicio, data_fim)

    if not df.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Gerar PDF do funcionário selecionado
            pdf_file = gerar_pdf(nome, cargo, dtcadastro, df)
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="Baixar Registro do Funcionario Filtrado",
                    data=f,
                    file_name=f"Relatorio_Ponto_{nome.replace(' ', '_')}.pdf",
                    mime="application/pdf",use_container_width=True
                )
            os.remove(pdf_file)  # Remover arquivo temporário

        with col2:
            if st.button("Solicitar de Todos os Funcionários",use_container_width=True):
                # Consultar registros de todos os funcionários no período selecionado
                cursor.execute("""
                    SELECT FUNC.ID, FUNC.NOME, FUNC.CARGO, FUNC.DTCADASTRO, REG.DATA, REG.CHEGADA, REG.SAIDA_ALMOCO, REG.RETORNO_ALMOCO, REG.SAIDA
                    FROM REGISTROS REG
                    JOIN FUNCIONARIOS FUNC ON REG.FUNCIONARIO_ID = FUNC.ID
                    WHERE REG.DATA BETWEEN %s AND %s
                    ORDER BY FUNC.ID, REG.DATA
                """, (data_inicio, data_fim))
                registros = cursor.fetchall()

                if registros:
                    # Agrupar os registros por funcionário
                    funcionarios_registros = {}
                    for registro in registros:
                        funcionario_id = registro[0]
                        if funcionario_id not in funcionarios_registros:
                            funcionarios_registros[funcionario_id] = {
                                "nome": registro[1],
                                "cargo": registro[2],
                                "admissao": registro[3],
                                "registros": []
                            }
                        funcionarios_registros[funcionario_id]["registros"].append(registro[4:])

                    # Criar PDFs individuais para cada funcionário e armazená-los em um arquivo ZIP
                    zip_buffer = BytesIO()
                    with ZipFile(zip_buffer, "w") as zip_file:
                        for funcionario_id, dados in funcionarios_registros.items():
                            # Criar DataFrame para os registros do funcionário
                            registros_df = pd.DataFrame(
                                dados["registros"],
                                columns=["Data", "Chegada", "Saída Almoço", "Retorno Almoço", "Saída"]
                            )

                            # Gerar um range de datas para incluir todos os dias no período
                            todas_as_datas = pd.date_range(start=data_inicio, end=data_fim)
                            datas_df = pd.DataFrame({"Data": todas_as_datas})

                            # Mesclar para garantir que todos os dias estejam presentes
                            registros_df["Data"] = pd.to_datetime(registros_df["Data"], errors='coerce')
                            registros_completos = datas_df.merge(
                                registros_df,
                                on="Data",
                                how="left"
                            )

                            # Substituir valores nulos por vazio (campo em branco)
                            registros_completos.fillna("", inplace=True)

                            # Adicionar a coluna "Data e Dia" com nomes de dias em português (abreviados)
                            registros_completos["Data e Dia"] = registros_completos["Data"].dt.strftime("%d/%m/%Y (%a)")
                            registros_completos["Data e Dia"] = registros_completos["Data e Dia"].replace({
                                "Mon": "Seg",
                                "Tue": "Ter",
                                "Wed": "Qua",
                                "Thu": "Qui",
                                "Fri": "Sex",
                                "Sat": "Sab",
                                "Sun": "Dom"
                            }, regex=True)

                            # Formatar horários para hh:mm:ss
                            for coluna in ["Chegada", "Saída Almoço", "Retorno Almoço", "Saída"]:
                                registros_completos[coluna] = registros_completos[coluna].apply(
                                    lambda x: x.strftime("%H:%M:%S") if isinstance(x, time) else x
                                )

                            # Gerar PDF para o funcionário
                            pdf_file = gerar_pdf(
                                dados["nome"],
                                dados["cargo"],
                                dados["admissao"],
                                registros_completos
                            )

                            # Adicionar o PDF ao arquivo ZIP
                            with open(pdf_file, "rb") as f:
                                zip_file.writestr(f"Relatorio_Ponto_{dados['nome'].replace(' ', '_')}.pdf", f.read())
                            os.remove(pdf_file)  # Remover arquivo temporário

                    # Fornecer o arquivo ZIP como download imediato
                    zip_buffer.seek(0)
                    st.download_button(
                        label="Baixar",
                        data=zip_buffer,
                        file_name="Relatorios_Ponto_Todos_Funcionarios.zip",
                        mime="application/zip",use_container_width=True
                    )
                else:
                    st.warning("Nenhum registro encontrado no período selecionado.")


def verificar_restricoes_ponto(cursor, usuario_id):
    """Verifica se o usuário está de férias ou já tem uma falta registrada no dia."""
    data_atual = datetime.now().date()

    # Verificar se o usuário está de férias
    cursor.execute("""
        SELECT COUNT(*) 
        FROM FERIAS 
        WHERE FUNCIONARIO_ID = %s AND %s BETWEEN DATA_INICIO AND DATA_FIM
    """, (usuario_id, data_atual))
    esta_de_ferias = cursor.fetchone()[0] > 0

    # Verificar se já há uma falta registrada para o usuário
    cursor.execute("""
        SELECT COUNT(*) 
        FROM FALTAS 
        WHERE FUNCIONARIO_ID = %s AND DATA = %s
    """, (usuario_id, data_atual))
    falta_registrada = cursor.fetchone()[0] > 0

    if esta_de_ferias:
        st.error("Você está de férias e não pode registrar o ponto.")
        return False
    elif falta_registrada:
        st.error("Você já possui uma falta registrada para hoje. Não é possível bater o ponto.")
        return False

    return True

#Tela para o Registro do ponto

def tela_funcionario():
    if "usuario" not in st.session_state:
        st.warning("Faça login para acessar esta área.")
        return

    usuario = st.session_state["usuario"]

    nome_completo = usuario['nome']
    primeiro_nome, primeiro_sobrenome = nome_completo.split()[:2]
    st.markdown(f"<h1 style='text-align: center;font-size: 40px;'>Olá, {primeiro_nome} {primeiro_sobrenome}!</h1>", unsafe_allow_html=True)
    st.write('______________________________________________')


    # Carregar feriados de um arquivo externo
    def carregar_feriados():
        caminho_feriados = Path("feriados.json")
        if caminho_feriados.exists():
            with open(caminho_feriados, "r", encoding="utf-8") as f:
                return [datetime.strptime(data, "%Y-%m-%d").date() for data in json.load(f)]
        else:
            st.error("Arquivo de feriados não encontrado. Por favor, crie um arquivo 'feriados.json'.")
            return []

    feriados = carregar_feriados()

    def verificar_ausencias(cursor):
        data_atual = datetime.now().date()

        # 🔍 Buscar o último dia que o funcionário bateu ponto
        cursor.execute("""
            SELECT MAX(DATA)
            FROM REGISTROS
            WHERE FUNCIONARIO_ID = %s
        """, (usuario["id"],))
        ultimo_ponto = cursor.fetchone()[0]

        if not ultimo_ponto:
            st.error("Não foi possível obter o último registro de ponto.")
            return False

        # 📅 Gerar os dias a partir do último registro até ONTEM
        dias_faltantes = []
        for i in range((data_atual - ultimo_ponto).days):
            dia = ultimo_ponto + timedelta(days=i + 1)

            # 🔹 Ignorar finais de semana e feriados
            if dia.weekday() >= 5 or dia in feriados:
                continue

            # 🔹 Ignorar o dia atual (pois o funcionário ainda pode registrar o ponto)
            if dia == data_atual:
                continue  

            # 🔹 Verificar se o ponto já foi registrado nesse dia
            cursor.execute("""
                SELECT 1
                FROM REGISTROS
                WHERE FUNCIONARIO_ID = %s AND DATA = %s
            """, (usuario["id"], dia))
            registro_existe = cursor.fetchone()

            # 🔹 Verificar se já há uma falta registrada nesse dia
            cursor.execute("""
                SELECT 1
                FROM FALTAS
                WHERE FUNCIONARIO_ID = %s AND DATA = %s
            """, (usuario["id"], dia))
            falta_existe = cursor.fetchone()

            # 🔹 Verificar se o funcionário estava de férias nesse dia
            cursor.execute("""
                SELECT COUNT(*)
                FROM FERIAS
                WHERE FUNCIONARIO_ID = %s AND %s BETWEEN DATA_INICIO AND DATA_FIM
            """, (usuario["id"], dia))
            esta_de_ferias = cursor.fetchone()[0] > 0

            # 🔥 Se não há registro, falta ou férias, então é uma ausência
            if not registro_existe and not falta_existe and not esta_de_ferias:
                dias_faltantes.append(dia)

        # 🔹 Se houver faltas não justificadas, solicitar justificativa
        for data in sorted(dias_faltantes):
            justificativa_key = f"justificativa_{data}"
            if justificativa_key not in st.session_state:
                st.session_state[justificativa_key] = False

            if not st.session_state[justificativa_key]:
                st.warning(f"Você não registrou ponto no dia {data.strftime('%d/%m/%Y')}. Justifique a ausência")
                justificativa = st.text_area(f"Informe a justificativa para a falta no dia {data.strftime('%d/%m/%Y')} (mínimo 15 caracteres):", key=f"falta_{data}")
                documento = st.file_uploader(f"Anexe um documento para comprovar a ausência no dia {data.strftime('%d/%m/%Y')} (opcional):", type=["pdf"], key=f"anexo_{data}")

                if st.button("Salvar Justificativa", key=f"salvar_justificativa_{data}"):
                    if len(justificativa) < 15:
                        st.error("A justificativa deve ter no mínimo 15 caracteres.")
                    else:
                        documento_blob = None
                        if documento:
                            documento_blob = documento.read()

                        cursor.execute("""
                            INSERT INTO FALTAS (FUNCIONARIO_ID, DATA, HORA, JUSTIFICATIVA, DOCUMENTO)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (usuario["id"], data, datetime.now().time(), justificativa, documento_blob))
                        conn.commit()

                        st.success("Justificativa salva com sucesso!")
                        st.session_state[justificativa_key] = True
                        st.rerun()

        if any(not st.session_state.get(f"justificativa_{data}", False) for data in dias_faltantes):
            return False

        return True



    def calcular_horas_extras(cursor, registros, data_atual, funcionario_id):
        chegada = datetime.combine(data_atual, registros[0]) if registros and registros[0] else None
        saida = datetime.combine(data_atual, datetime.now().time()) if registros[3] is None else datetime.combine(data_atual, registros[3])
        intervalo_almoco = timedelta()

        if registros[1] and registros[2]:  # Verificar se há almoço registrado
            intervalo_almoco = datetime.combine(data_atual, registros[2]) - datetime.combine(data_atual, registros[1])

        total_horas = saida - chegada - intervalo_almoco
        limite_horas = timedelta(hours=8, minutes=40)  # Jornada padrão (8h40min)
        
        # Definição do horário limite para tolerância de saída (18:10)
        horario_saida_padrao = datetime.combine(data_atual, time(18, 0))  # 18:00
        horario_saida_tolerancia = horario_saida_padrao + timedelta(minutes=10)  # 18:10

        if saida > horario_saida_tolerancia:  # Apenas se passar das 18:10
            horas_extras = total_horas - limite_horas
            if horas_extras > timedelta(0):  # Apenas registra se houver hora extra positiva
                horas_extras_time = f"{horas_extras.seconds // 3600:02}:{(horas_extras.seconds // 60) % 60:02}:{horas_extras.seconds % 60:02}"
                cursor.execute(
                    """
                    UPDATE REGISTROS
                    SET HORAEXTRA = %s
                    WHERE FUNCIONARIO_ID = %s AND DATA = %s
                    """, (horas_extras_time, funcionario_id, data_atual)
                )
                conn.commit()


    def registrar_ponto(tipo, cursor):
        data_atual = datetime.now().date()
        hora_atual = datetime.now().time()

        cursor.execute(
            """
            SELECT CHEGADA, SAIDA_ALMOCO, RETORNO_ALMOCO, SAIDA
            FROM REGISTROS
            WHERE FUNCIONARIO_ID = %s AND DATA = %s
            """, (usuario["id"], data_atual)
        )
        registros = cursor.fetchone()

        chegada = registros[0] if registros else None
        saida_almoco = registros[1] if registros else None
        retorno_almoco = registros[2] if registros else None
        saida = registros[3] if registros else None

        if tipo == "SAIDA_ALMOCO" and not chegada:
            placeholder = st.empty() 
            placeholder.error("Chegada não registrada!")
            tm.sleep(2)
            placeholder.empty()
            return

        if tipo == "RETORNO_ALMOCO" and not saida_almoco:
            placeholder = st.empty() 
            placeholder.error("Saída do almoço não registrada!")
            tm.sleep(2)
            placeholder.empty()
            return

        if tipo == "SAIDA" and not retorno_almoco and saida_almoco:
            placeholder = st.empty() 
            placeholder.error("Chegada não registrada!")
            tm.sleep(2)
            placeholder.empty()
            return

        if tipo == "SAIDA":
            chegada = datetime.combine(data_atual, registros[0]) if registros and registros[0] else None
            saida = datetime.combine(data_atual, hora_atual)

            # Definição do horário limite para tolerância de saída (18:10)
            horario_saida_padrao = datetime.combine(data_atual, time(18, 0))  # 18:00
            horario_saida_tolerancia = horario_saida_padrao + timedelta(minutes=10)  # 18:10

            if "dialog_open" not in st.session_state:
                st.session_state.dialog_open = True

            if chegada and saida > horario_saida_tolerancia:  # Só verifica justificativa se ultrapassar 18:10
                @st.dialog("Justificativa para Hora Extra")
                def dialog_justificativa():
                    st.write("Você excedeu o limite de horas diárias. Por favor, informe a justificativa para as horas extras.")
                    justificativa = st.text_area("Justificativa (mínimo 15 caracteres):", key="justificativa_hora_extra")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Confirmar", use_container_width=True):
                            if len(justificativa) < 15:
                                st.error("A justificativa deve ter no mínimo 15 caracteres.")
                                return
                            else:
                                cursor.execute("""
                                    INSERT INTO registros (funcionario_id, data, justificativahoraextra, saida)
                                    VALUES (%s, %s, %s, %s)
                                    ON CONFLICT (funcionario_id, data)  -- 🔹 Define as colunas que podem gerar conflito
                                    DO UPDATE SET 
                                        justificativahoraextra = EXCLUDED.justificativahoraextra, 
                                        saida = EXCLUDED.saida;
                                """, (usuario["id"], data_atual, justificativa, hora_atual))

                                conn.commit()

                                calcular_horas_extras(cursor, registros, data_atual, usuario["id"])
                                st.success("Justificativa registrada e saída registrada com sucesso!")
                                st.rerun()

                    with col2:
                        if st.button("Cancelar", use_container_width=True):
                            st.warning("Registro de saída cancelado.")
                            st.session_state.dialog_open = False
                            st.rerun()

                dialog_justificativa()
                return

        cursor.execute(
            f"""
            SELECT {tipo}
            FROM REGISTROS
            WHERE FUNCIONARIO_ID = %s AND DATA = %s
            """, (usuario["id"], data_atual)
        )
        registro = cursor.fetchone()

        if registro and registro[0]:
            placeholder = st.empty()
            placeholder.warning(f"Já registrado!", icon="⚠️")
            tm.sleep(1)
            placeholder.empty()
        else:
            cursor.execute(f"""
                INSERT INTO registros (funcionario_id, data, {tipo})
                VALUES (%s, %s, %s)
                ON CONFLICT (funcionario_id, data)
                DO UPDATE SET {tipo} = EXCLUDED.{tipo};
            """, (usuario["id"], data_atual, hora_atual))

            conn.commit()
            placeholder = st.empty()
            placeholder.success(f"Registrado!", icon="✅")
            tm.sleep(1)
            placeholder.empty()

    

    conn = conexao_persistente
    if conn:
        cursor = conexao_persistente.cursor()

        if not verificar_ausencias(cursor) or (not verificar_restricoes_ponto(cursor, usuario["id"])):
            return        
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

    if conn:
        cursor = conexao_persistente.cursor()
        data_atual = datetime.now().date()

        cursor.execute("""
            SELECT CHEGADA, SAIDA_ALMOCO, RETORNO_ALMOCO, SAIDA
            FROM REGISTROS
            WHERE FUNCIONARIO_ID = %s AND DATA = %s
        """, (usuario["id"], data_atual))
        registros = cursor.fetchone()

        #exibindo os registros
        if registros:
            st.markdown("<h1 style='text-align: center; font-size: 40px;'>Registros de Hoje:</h1>", unsafe_allow_html=True)
            data_atual = datetime.now().strftime("%Y-%m-%d")
            df = pd.DataFrame([registros] ,columns=["Chegada", "Saída Almoço", "Retorno Almoço", "Saída"])
            df = df.fillna("Não registrado")

            for col in ["Chegada", "Saída Almoço", "Retorno Almoço", "Saída"]:
                df[col] = df[col].apply(
                    lambda x: pd.to_datetime(f"{data_atual} {x}", errors='coerce').strftime("%H:%M:%S") 
                    if x != "Não registrado" else x
                )

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



#Manutenção do ponto caso o funcionário não esqueça de registrar o ponto
def tela_registro_ponto_manual():
    st.markdown("<h1 style='text-align: center;'>Registro de Ponto Manual</h1>", unsafe_allow_html=True)

    # Conexão com o banco de dados
    conn = conexao_persistente
    if not conn:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    cursor = conn.cursor()
    cursor.execute("ROLLBACK")

    # Selecionar funcionário
    cursor.execute("SELECT ID, NOME FROM FUNCIONARIOS ORDER BY NOME")
    funcionarios = cursor.fetchall()
    opcoes_funcionarios = {f"{nome}": id_func for id_func, nome in funcionarios}

    funcionario_selecionado = st.selectbox("Selecione o Funcionário:", options=opcoes_funcionarios.keys())

    if not funcionario_selecionado:
        st.warning("Selecione um funcionário para continuar.")
        return

    funcionario_id = opcoes_funcionarios[funcionario_selecionado]

    # Selecionar data do registro
    data_selecionada = st.date_input("Selecione a data do registro:", datetime.now().date(), format="DD/MM/YYYY")

    # Verificar se o funcionário já tem registro de férias ou falta na data
    cursor.execute("""
        SELECT COUNT(*) FROM FERIAS
        WHERE FUNCIONARIO_ID = %s AND %s BETWEEN DATA_INICIO AND DATA_FIM
    """, (funcionario_id, data_selecionada))
    esta_de_ferias = cursor.fetchone()[0] > 0

    cursor.execute("""
        SELECT COUNT(*) FROM FALTAS
        WHERE FUNCIONARIO_ID = %s AND DATA = %s
    """, (funcionario_id, data_selecionada))
    falta_registrada = cursor.fetchone()[0] > 0

    if esta_de_ferias:
        st.warning("Este funcionário está de férias na data selecionada e não pode registrar ponto.")
        return

    if falta_registrada:
        st.warning("Este funcionário já possui uma falta registrada para a data selecionada e não pode registrar presença.")
        return

    # Função para registrar o ponto manualmente
    def registrar_ponto_manual(tipo, cursor):
        hora_atual = st.time_input(f"{tipo}:", key=f"hora_{tipo}")

        if st.button(f"{tipo}", key=f"registrar_{tipo}", use_container_width=True):
            # Verificar se o registro para a data já existe
            cursor.execute("""
                SELECT 1 FROM REGISTROS
                WHERE FUNCIONARIO_ID = %s AND DATA = %s
            """, (funcionario_id, data_selecionada))
            registro_existe = cursor.fetchone()

            try:
                if not registro_existe:
                    # Inserir novo registro
                    cursor.execute("""
                        INSERT INTO REGISTROS (FUNCIONARIO_ID, DATA, """ + tipo + """)
                        VALUES (%s, %s, %s)
                    """, (funcionario_id, data_selecionada, hora_atual))
                else:
                    # Atualizar registro existente
                    cursor.execute("""
                        UPDATE REGISTROS
                        SET """ + tipo + """ = %s
                        WHERE FUNCIONARIO_ID = %s AND DATA = %s
                    """, (hora_atual, funcionario_id, data_selecionada))

                conn.commit()
                placeholder = st.empty()
                placeholder.success(f"Registrado!", icon="✅")
                tm.sleep(1)
                placeholder.empty()
            except Exception as e:
                st.error(f"Erro ao registrar {tipo}: {e}")

    # Botões para registrar pontos
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        registrar_ponto_manual("Chegada", cursor)
    with col2:
        registrar_ponto_manual("Saida_Almoco", cursor)
    with col3:
        registrar_ponto_manual("Retorno_Almoco", cursor)
    with col4:
        registrar_ponto_manual("Saida", cursor)

    # Exibir registros do dia selecionado
    cursor.execute("""
        SELECT CHEGADA, SAIDA_ALMOCO, RETORNO_ALMOCO, SAIDA
        FROM REGISTROS
        WHERE FUNCIONARIO_ID = %s AND DATA = %s
    """, (funcionario_id, data_selecionada))
    registros = cursor.fetchone()

    if registros:
        st.markdown("<h2 style='text-align: center;'>Registros do Dia</h2>", unsafe_allow_html=True)
        df = pd.DataFrame([registros], columns=["Chegada", "Saída Almoço", "Retorno Almoço", "Saída"])
        df = df.fillna("Não registrado")

        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum registro encontrado para a data selecionada.")


def tela_banco_horas():
    usuario = st.session_state["usuario"]
    st.title("Banco de Horas")

    conn = conexao_persistente
    if conn:
        cursor = conexao_persistente.cursor()
        try:
            # Consulta ajustada para excluir valores nulos
            cursor.execute("""
                SELECT DATA, HORAEXTRA,JUSTIFICATIVAHORAEXTRA
                FROM REGISTROS
                WHERE FUNCIONARIO_ID = %s AND HORAEXTRA IS NOT NULL
                ORDER BY DATA
            """, (usuario["id"],))
            registros = cursor.fetchall()

            if registros:
                # Criando o DataFrame
                df = pd.DataFrame(registros, columns=["Data", "Hora Extra", "Justifivativa"])

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

                st.dataframe(df,hide_index=True,use_container_width=True)

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
                    WHERE id = %s
                """, (usuario["id"],))
                registro = cursor.fetchone()

                if not registro or registro[0] != gerar_hash_senha(senha_atual):
                    st.error("Senha atual incorreta.")
                else:
                    # Atualizar a senha no banco de dados
                    nova_senha_hash = gerar_hash_senha(nova_senha)
                    cursor.execute("""
                        UPDATE funcionarios
                        SET senha = %s
                        WHERE id = %s
                    """, (nova_senha_hash, usuario["id"]))
                    conn.commit()
                    st.success("Senha alterada com sucesso!")
            else:
                st.error("Erro ao conectar ao banco de dados.")



#alterar dados cadastrais dos usuarios


# 🔹 Função para limpar entradas inválidas
def limpar_texto(valor, tipo, max_length):
    """Remove caracteres inválidos e limita o tamanho do campo"""
    if not valor:
        return ""

    if tipo in ["nome", "cargo"]:
        valor = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ\s]", "", valor)  # Apenas letras e espaços
    
    if tipo == "username":
        valor = re.sub(r"[^A-Za-z0-9]", "", valor)  # Apenas letras e números

    return valor[:max_length]  # Limita o número de caracteres

# 🔹 Validação do email
def validar_email(valor):
    """Valida se o email está no formato correto"""
    if not valor or len(valor) > 100:
        return False
    return bool(re.fullmatch(r"^[\w\.-]+@[\w\.-]+\.\w+$", valor))

# 🔹 Função de manutenção de usuários
def tela_manutencao_funcionarios():
    st.markdown("<h1 style='text-align: center;'>Manutenção de Funcionários</h1>", unsafe_allow_html=True)

    # Listar os usuários cadastrados
    usuarios = listar_usuarios()
    if not usuarios:
        st.warning("Nenhum funcionário encontrado.")
        return

    # Criar um DataFrame para facilitar o filtro
    df_usuarios = pd.DataFrame(usuarios, columns=["ID", "Nome", "Username", "Email", "DtContratacao", "Administrador", "Agendamento", "Edita_ponto"])

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
    id_usuario = int(funcionario["ID"])
    nome_atual = funcionario["Nome"]
    email_atual = funcionario["Email"]
    dt_contratacao_atual = funcionario["DtContratacao"]

    # 🔹 Converter valores dos checkboxes corretamente ('0' → False, '1' → True)
    administrador_atual = funcionario["Administrador"] == '1'
    agendamento_atual = funcionario["Agendamento"] == '1'
    edita_ponto_atual = funcionario["Edita_ponto"] == '1'

    # 🔹 Atualizar valores no session_state ao trocar de usuário
    if "usuario_selecionado" not in st.session_state or st.session_state.usuario_selecionado != funcionario_selecionado:
        st.session_state.usuario_selecionado = funcionario_selecionado
        st.session_state.administrador_atual = administrador_atual
        st.session_state.agendamento_atual = agendamento_atual
        st.session_state.edita_ponto_atual = edita_ponto_atual

    # Configurar os checkboxes em colunas
    col1, col2 = st.columns(2)

    with col1:
        alterar_dados = st.checkbox("Alterar Dados Cadastrais", value=True)

    with col2:
        alterar_senha = st.checkbox("Alterar Senha", value=False)

    if alterar_dados:
        with st.form("form_dados_cadastrais"):
            novo_nome = st.text_input("Nome do Funcionário", value=nome_atual, max_chars=100)
            novo_cargo = st.text_input("Cargo do Funcionário", max_chars=50)
            novo_email = st.text_input("Email", value=email_atual, max_chars=100)
            data_padrao = datetime.today().date()  # Usa a data de hoje como padrão
            nova_dt_contratacao = st.date_input("Data de Contratação", format='DD/MM/YYYY', value=dt_contratacao_atual if dt_contratacao_atual else data_padrao)


            col3, col4, col5 = st.columns(3)
            with col3:
                administrador = st.checkbox("Acesso Administrativo", value=st.session_state.administrador_atual, key="checkbox_administrador")
            with col4:
                agendamento = st.checkbox("Acesso à Agenda", value=st.session_state.agendamento_atual, key="checkbox_agendamento")
            with col5:
                edita_ponto = st.checkbox("Alterar Ponto", value=st.session_state.edita_ponto_atual, key="checkbox_edita_ponto")

            submit_button = st.form_submit_button("Salvar Alterações", use_container_width=True)

        if submit_button:
            erros = []

            # 🔹 Aplicar filtro nos campos antes da validação
            novo_nome = limpar_texto(novo_nome, "nome", 100)
            novo_cargo = limpar_texto(novo_cargo, "cargo", 50)

            # 🔹 Validações
            if not novo_nome or len(novo_nome.split()) < 2:
                erros.append("❌ O nome deve conter pelo menos um sobrenome.")

            if len(novo_nome) > 100:
                erros.append("❌ O nome ultrapassa 100 caracteres.")

            if not novo_cargo:
                erros.append("❌ O cargo não pode estar vazio.")

            if len(novo_cargo) > 50:
                erros.append("❌ O cargo ultrapassa 50 caracteres.")

            if re.search(r"[^A-Za-zÀ-ÖØ-öø-ÿ\s]", novo_cargo):
                erros.append("❌ O cargo deve conter apenas letras e espaços.")

            if not validar_email(novo_email):
                erros.append("❌ O email informado não é válido.")

            # 🔹 Exibir erros ou atualizar no banco
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                conn = conexao_persistente
                if conn:
                    cursor = conexao_persistente.cursor()
                    try:
                        cursor.execute("ROLLBACK")  # Garante que não há transações pendentes antes da atualização

                        cursor.execute("""
                            UPDATE funcionarios 
                            SET nome = %s, email = %s, dtcontratacao = %s, cargo = %s, administrador = %s, agendamento = %s, edita_ponto = %s  
                            WHERE id = %s
                        """, (
                            novo_nome,novo_email,nova_dt_contratacao,novo_cargo,int(administrador), int(agendamento), int(edita_ponto),id_usuario
                        ))

                        conn.commit()
                        st.success(f"Dados do funcionário {novo_nome} atualizados com sucesso! ✅")

                    except Exception as e:
                        conn.rollback()  # Desfaz qualquer alteração em caso de erro
                        st.error(f"Erro ao atualizar os dados do funcionário: {e}")

    if alterar_senha:
        with st.form("form_alterar_senha"):
            nova_senha = st.text_input("Digite a nova senha", type="password", max_chars=100)
            confirmar_senha = st.text_input("Confirme a nova senha", type="password", max_chars=100)

            submit_senha = st.form_submit_button("Alterar Senha", use_container_width=True)

            if submit_senha:
                if len(nova_senha) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                else:
                    conn = conexao_persistente
                    if conn:
                        cursor = conexao_persistente.cursor()
                        try:
                            cursor.execute("UPDATE funcionarios SET senha = %s WHERE id = %s", (criptografar_senha(nova_senha), id_usuario))
                            conn.commit()
                            st.success("Senha alterada com sucesso! ✅")
                        except Exception as e:
                            st.error(f"Erro ao atualizar a senha: {e}")



### Tela para cadastrar usuario 


# 🔹 Função para limpar entradas
def limpar_texto(valor, tipo, max_length):
    """Remove caracteres inválidos e limita o tamanho do campo"""
    if not valor:
        return ""

    if tipo == "nome" or tipo == "cargo":
        valor = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ\s]", "", valor)  # Apenas letras e espaços
    
    if tipo == "username":
        valor = re.sub(r"[^A-Za-z0-9]", "", valor)  # Apenas letras e números

    return valor[:max_length]  # Limita o número de caracteres

# 🔹 Validação do email
def validar_email(valor):
    """Valida se o email está no formato correto"""
    if not valor or len(valor) > 100:
        return False
    return bool(re.fullmatch(r"^[\w\.-]+@[\w\.-]+\.\w+$", valor))

def tela_administracao():
    st.markdown("<h1 style='text-align: center;'>Cadastrar Funcionário</h1>", unsafe_allow_html=True)

    # Variáveis de estado para limpar os campos
    if "form_submitted" not in st.session_state:
        st.session_state["form_submitted"] = False

    with st.form("form_cadastro"):
        nome = st.text_input("Nome do Funcionário", max_chars=100, value="" if st.session_state["form_submitted"] else None)
        username = st.text_input("Nome de Usuário", max_chars=50, value="" if st.session_state["form_submitted"] else None)
        senha = st.text_input("Senha", type="password", max_chars=100, value="" if st.session_state["form_submitted"] else "")
        confirmar_senha = st.text_input("Confirme a Senha", type="password", max_chars=100, value="" if st.session_state["form_submitted"] else "")
        cargo = st.text_input("Cargo", max_chars=50, value="" if st.session_state["form_submitted"] else None)
        email = st.text_input("Email", max_chars=100, value="" if st.session_state["form_submitted"] else None)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            administrador = st.checkbox("Acesso Administrativo", value=False if st.session_state["form_submitted"] else None)
        with col2:
            agendamento = st.checkbox("Acesso a Agenda", value=False if st.session_state["form_submitted"] else None)
        with col3:
            edita_ponto = st.checkbox("Alterar Ponto", value=False if st.session_state["form_submitted"] else None)
        
        submit_button = st.form_submit_button("Cadastrar", use_container_width=True)

        if submit_button:
            erros = []

            # 🔹 Aplicar filtro nos campos antes da validação
            nome = limpar_texto(nome, "nome", 100)
            cargo = limpar_texto(cargo, "cargo", 50)
            username = limpar_texto(username, "username", 50)

            # 🔹 Validações
            if not nome or len(nome.split()) < 2:
                erros.append("❌ O nome deve conter pelo menos um sobrenome.")

            if not nome:
                erros.append("❌ O nome não pode estar vazio.")

            if len(nome) > 100:
                erros.append("❌ O nome ultrapassa 100 caracteres.")

            if not username:
                erros.append("❌ O nome de usuário não pode estar vazio.")

            if len(username) > 50:
                erros.append("❌ O nome de usuário ultrapassa 50 caracteres.")

            if username_em_uso(username):
                erros.append("❌ Este nome de usuário já está em uso. Escolha outro.")

            if not senha or len(senha) < 6:
                erros.append("❌ A senha deve ter pelo menos 6 caracteres.")

            if len(senha) > 100:
                erros.append("❌ A senha ultrapassa 100 caracteres.")

            if senha != confirmar_senha:
                erros.append("❌ As senhas não coincidem. Por favor, tente novamente.")

            if not cargo:
                erros.append("❌ O cargo não pode estar vazio.")

            if len(cargo) > 50:
                erros.append("❌ O cargo ultrapassa 50 caracteres.")

            if re.search(r"[^A-Za-zÀ-ÖØ-öø-ÿ\s]", cargo):  # Verifica se tem número ou caractere especial
                erros.append("❌ O cargo deve conter apenas letras e espaços.")

            if not validar_email(email):
                erros.append("❌ O email informado não é válido.")

            # 🔹 Exibir erros ou cadastrar no banco
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                conn = conexao_persistente
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("ROLLBACK")
                    senha_criptografada = criptografar_senha(senha)
                    try:
                        # Converta os checkboxes para 1 ou 0
                        admin_valor = 1 if administrador else 0
                        agendamento_valor = 1 if agendamento else 0
                        alterar_ponto = 1 if edita_ponto else 0

                        # 🔹 Inserir novo usuário no banco de dados
                        cursor.execute("""
                            INSERT INTO funcionarios (nome, username, senha, cargo, administrador, agendamento, email, edita_ponto)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (nome, username, senha_criptografada, cargo, admin_valor, agendamento_valor, email, alterar_ponto))

                        conn.commit()

                        placeholder = st.empty() 
                        placeholder.success(f"Funcionário {nome} cadastrado com sucesso! ✅")
                        tm.sleep(3)

                        # Marca o formulário como submetido para limpar os campos
                        st.session_state["form_submitted"] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar funcionário: {e}")

def username_em_uso(username):
    """Verifica se o username já está em uso no banco de dados."""
    conn = conexao_persistente
    if conn:
        cursor = conn.cursor()
        cursor.execute("ROLLBACK")
        cursor.execute("SELECT COUNT(*) FROM funcionarios WHERE username = %s", (username,))
        resultado = cursor.fetchone()
        return resultado[0] > 0  # Retorna True se já existir, False se estiver disponível
    return False





def tela_admin_faltas():
    st.markdown("<h1 style='text-align: center;'>Faltas Registradas</h1>", unsafe_allow_html=True)

    # Conexão com o banco de dados
    conn = conexao_persistente
    if conn:
        cursor = conn.cursor()
        cursor.execute("ROLLBACK")
        cursor.execute("""
            SELECT F.FUNCIONARIO_ID, F.DATA, F.JUSTIFICATIVA, F.DOCUMENTO, FUNC.NOME
            FROM FALTAS F
            JOIN FUNCIONARIOS FUNC ON F.FUNCIONARIO_ID = FUNC.ID
            ORDER BY F.DATA DESC
        """)
        registros = cursor.fetchall()

        if registros:
            # Criar dataframe para exibição
            dados = []
            documentos = []  # Lista para armazenar documentos e informações associadas

            for registro in registros:
                id_funcionario, data, justificativa, documento, nome = registro
                possui_documento = "Sim" if documento else "Não"
                dados.append({
                    "X": False,
                    "Data": data.strftime("%d/%m/%Y"),
                    "Funcionário": nome,
                    "Justificativa": justificativa,
                    "Anexo": possui_documento
                })

                # Adicionar documento para referência
                documentos.append({
                    "Funcionário": nome,
                    "Data": data.strftime("%d/%m/%Y"),
                    "Anexo": documento
                })

            # Criar dataframe
            df = pd.DataFrame(dados)

            # Adicionar filtro de funcionário com múltipla seleção
            funcionarios = df["Funcionário"].unique()
            funcionarios_selecionados = st.multiselect("Selecione os Funcionários", options=funcionarios, default=[])

            # Filtrar dataframe com base na seleção
            if funcionarios_selecionados:
                df = df[df["Funcionário"].isin(funcionarios_selecionados)]

            # Configurar colunas para DataFrame interativo
            edited_df = st.data_editor(
                df,
                column_config={
                    "X": st.column_config.CheckboxColumn(
                        "X",
                        help="Marque para selecionar os documentos que deseja baixar.",
                    ),
                    "Data": "Data",
                    "Funcionário": "Funcionário",
                    "Justificativa": "Justificativa",
                    "Anexo": "Anexo",
                },
                hide_index=True,disabled=("Data","Funcionário" ,"Justificativa","Anexo"),
                use_container_width=True,
            )

            # Coletar documentos selecionados para download
            selecionados = edited_df[edited_df["X"] == True]
            if not selecionados.empty:
                for _, row in selecionados.iterrows():
                    doc_info = next((doc for doc in documentos if doc["Funcionário"] == row["Funcionário"] and doc["Data"] == row["Data"]), None)
                    if doc_info and doc_info["Anexo"]:
                        st.download_button(
                            label="Baixar Documento",
                            data=bytes(doc_info["Anexo"]), 
                            file_name=f"documento_{row['Funcionário']}.pdf",
                            mime="application/pdf",
                        )
            else:
                ''#st.warning("Nenhum documento foi selecionado para download.")
        else:
            st.info("Nenhuma falta registrada até o momento.")
    else:
        st.error("Erro na conexão com o banco de dados.")


#falta do usuario logado

def tela_usuario_faltas():
    usuario = st.session_state["usuario"]
    st.markdown(f"<h1 style='text-align: center;'>Minhas Faltas</h1>", unsafe_allow_html=True)

    # Conexão com o banco de dados
    conn = conexao_persistente
    if conn:
        cursor = conn.cursor()
        cursor.execute("ROLLBACK")
        cursor.execute("""
            SELECT DATA, JUSTIFICATIVA, DOCUMENTO
            FROM FALTAS
            WHERE FUNCIONARIO_ID = %s
            ORDER BY DATA DESC
        """, (usuario["id"],))
        registros = cursor.fetchall()

        if registros:
            # Criar dataframe para exibição
            dados = []
            documentos = []  # Lista para armazenar documentos e informações associadas

            for registro in registros:
                data, justificativa, documento = registro
                possui_documento = "Sim" if documento else "Não"
                dados.append({
                    "X": False,
                    "Data": data.strftime("%d/%m/%Y"),
                    "Justificativa": justificativa,
                    "Anexo": possui_documento
                })

                # Adicionar documento para referência
                documentos.append({
                    "Data": data.strftime("%d/%m/%Y"),
                    "Anexo": documento
                })

            # Criar dataframe
            df = pd.DataFrame(dados)

            # Configurar colunas para DataFrame interativo
            edited_df = st.data_editor(
                df,
                column_config={
                    "X": st.column_config.CheckboxColumn(
                        "X",
                        help="Marque para selecionar os documentos que deseja baixar.",
                    ),
                    "Data": "Data",
                    "Justificativa": "Justificativa",
                    "Anexo": "Anexo",
                },
                hide_index=True,disabled=("Data", "Justificativa","Anexo"),
                use_container_width=True,
            )

            # Coletar documentos selecionados para download
            selecionados = edited_df[edited_df["X"] == True]
            if not selecionados.empty:
                for _, row in selecionados.iterrows():
                    doc_info = next((doc for doc in documentos if doc["Data"] == row["Data"]), None)
                    if doc_info and doc_info["Anexo"]:
                        st.download_button(
                            label="Baixar Documento",
                            data=bytes(doc_info["Anexo"]), 
                            file_name=f"documento_{row['Data']}.pdf",
                            mime="application/pdf",
                        )
            else:
                ''#st.warning("Nenhum documento foi selecionado para download.")
        else:
            st.info("Você não possui faltas registradas!")
    else:
        st.error("Não foi possível conectar ao banco de dados.")


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
    """Adiciona um evento ao Google Calendar"""
    try:
        evento = {
            'summary': titulo,  # Título do evento
            'start': {'dateTime': f"{inicio}T00:00:00-03:00", 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': f"{fim}T23:59:59-03:00", 'timeZone': 'America/Sao_Paulo'},
            'attendees': [{'email': email} for email in emails_convidados] if emails_convidados else [],
        }

        # Envia o evento para o Google Calendar
        servico.events().insert(calendarId=calendario_id, body=evento).execute()
        #print("Evento criado com sucesso:", json.dumps(response, indent=2))
    except:
        ''
    

def obter_usuario_logado():
    usuario = st.session_state.get("usuario", {})
    
    if isinstance(usuario, dict):  # Certifique-se de que 'usuario' é um dicionário
        nome_completo = usuario.get("nome", "Desconhecido")  # Ajuste para pegar o campo correto
    else:
        nome_completo = usuario  # Se for uma string diretamente
    
    partes_nome = nome_completo.split()
    return f"{partes_nome[0]} {partes_nome[1]}" if len(partes_nome) >= 2 else nome_completo

def exibir_formulario_ferias():
    creds = autenticar_google_calendar()
    calendario_id = obter_id_calendario(creds)
    servico = build('calendar', 'v3', credentials=creds)
    
    st.markdown("<h1 style='text-align: center;'>Marcar Férias</h1>", unsafe_allow_html=True)
    
    conn = conexao_persistente
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("ROLLBACK")
            cursor.execute("""
                SELECT ID, NOME, EMAIL
                FROM FUNCIONARIOS
                ORDER BY 2
            """)
            funcionarios = cursor.fetchall()
        except Exception as e:
            st.error(f"Erro ao carregar os funcionários: {e}")
            return
    else:
        st.error("Erro na conexão com o banco de dados.")
        return

    if not funcionarios:
        st.error("Nenhum funcionário encontrado no banco de dados.")
        return
    
    if "funcionarios_dict" not in st.session_state:
        st.session_state["funcionarios_dict"] = {
            f"{nome}": {"id": id, "email": email} for id, nome, email in funcionarios
        }
    
    usuario_logado = obter_usuario_logado()  # Captura usuário logado da sessão
    
    # Inicializar o estado, se necessário
    if "funcionario_selecionado" not in st.session_state:
        primeiro_funcionario = list(st.session_state["funcionarios_dict"].keys())[0]
        st.session_state["funcionario_selecionado"] = primeiro_funcionario
        st.session_state["emails_convidados"] = st.session_state["funcionarios_dict"][primeiro_funcionario]["email"] or ""

    # Atualizar os e-mails convidados ao mudar o funcionário
    def update_emails_convidados():
        """Atualiza os e-mails convidados no estado ao mudar o funcionário."""
        funcionario_atual = st.session_state["funcionario_selecionado"]
        if funcionario_atual in st.session_state["funcionarios_dict"]:
            st.session_state["emails_convidados"] = st.session_state["funcionarios_dict"][funcionario_atual]["email"] or ""

    funcionario_selecionado = st.selectbox(
        "Selecione o Funcionário",
        options=list(st.session_state["funcionarios_dict"].keys()),
        index=list(st.session_state["funcionarios_dict"].keys()).index(st.session_state["funcionario_selecionado"]),
        key="funcionario_selecionado",
        on_change=update_emails_convidados
    )
    
    with st.form("formulario_ferias"):
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data de Início", format="DD/MM/YYYY")
        with col2:
            data_fim = st.date_input("Data de Fim", format="DD/MM/YYYY")
        
        ano_referencia = f"{data_inicio.year-1}/{data_inicio.year}"
        
        col3, col4 = st.columns(2)
        with col3:
            st.text_input("Ano de Referência", ano_referencia)
        with col4:
            st.text_input("Responsável pela Autorização", usuario_logado, disabled=True)
        
        emails_convidados = st.text_area(
            "E-mails:",
            placeholder="exemplo1@dominio.com, exemplo2@dominio.com",
            key="emails_convidados",
        )
        
        botao_submeter = st.form_submit_button("Marcar Férias", use_container_width=True)
        
        if botao_submeter:
            if data_inicio > data_fim:
                st.error("A data de início não pode ser maior que a data de fim.")
            elif not funcionario_selecionado:
                st.error("O funcionário é obrigatório.")
            else:
                funcionario_id = st.session_state["funcionarios_dict"][funcionario_selecionado]["id"]
                titulo = f"Férias: {funcionario_selecionado.split(' ')[0]}"
                emails_formatados = [email.strip() for email in emails_convidados.split(",") if email.strip()]
                registrado_em = datetime.now().strftime('%Y-%m-%d')
                
                adicionar_evento_calendario(
                    servico,
                    calendario_id,
                    titulo,
                    data_inicio.strftime('%Y-%m-%d'),
                    (data_fim + timedelta(days=1)).strftime('%Y-%m-%d'),
                    emails_formatados,
                )
                
                if conn:
                    try:
                        cursor.execute("""
                            INSERT INTO FERIAS (FUNCIONARIO_ID, DATA_INICIO, DATA_FIM, ANO_REFERENCIA, RESPONSAVEL_AUTORIZACAO, EMAILS_ENVOLVIDOS,REGISTRADO_EM)
                            VALUES (%s, %s, %s, %s, %s, %s,%s)
                        """, (funcionario_id, data_inicio, data_fim, ano_referencia, usuario_logado, ','.join(emails_formatados),registrado_em))

                        conn.commit()
                        st.success(f"Férias de {funcionario_selecionado.split(' ')[0]} adicionadas ao calendário e salvas no banco de dados!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco de dados: {e}")





def minhas_ferias_marcadas():
    usuario = st.session_state["usuario"]
    st.markdown("<h1 style='text-align: center;'>Minhas Férias</h1>", unsafe_allow_html=True)

    # Obter a conexão com o banco de dados
    conn = conexao_persistente
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("ROLLBACK")
            # Buscar todas as férias marcadas
            cursor.execute("""
                SELECT 
                    f.NOME AS Funcionario,
                    ferias.DATA_INICIO AS DataInicio,
                    ferias.DATA_FIM AS DataFim,
                    ferias.REGISTRADO_EM AS RegistradoEm,
                    ferias.ano_referencia
                FROM FERIAS 
                JOIN FUNCIONARIOS f ON ferias.FUNCIONARIO_ID = f.ID
                WHERE FUNCIONARIO_ID = %s
                ORDER BY ferias.DATA_INICIO DESC
            """,(usuario["id"],))
            registros = cursor.fetchall()

            if registros:
                # Criar o DataFrame para exibir os dados
                df = pd.DataFrame(
                    registros,
                    columns=["Funcionário", "Data de Início", "Data Final","Aprovado em","Referência"]
                )

                # Formatando as colunas de data para exibição
                df["Data de Início"] = pd.to_datetime(df["Data de Início"]).dt.strftime("%d/%m/%Y")
                df["Data Final"] = pd.to_datetime(df["Data Final"]).dt.strftime("%d/%m/%Y")
                df["Aprovado em"] = pd.to_datetime(df["Aprovado em"]).dt.strftime("%d/%m/%Y")

                # Exibir o DataFrame no Streamlit
                st.data_editor(df,disabled=True,hide_index=True,use_container_width=True )

            else:
                st.warning("Nenhuma férias marcada no momento.")
        except Exception as e:
            st.error(f"Erro ao buscar férias marcadas: {e}")
        finally:
            ''
    else:
        st.error("Erro na conexão com o banco de dados.")

#Listar férias de todos os funcionários 
def ferias_marcadas():
    st.markdown("<h1 style='text-align: center;'>Férias Agendadas</h1>", unsafe_allow_html=True)

    # Obter a conexão com o banco de dados
    conn = conexao_persistente
    if conn:
        try:
            cursor = conexao_persistente.cursor()
            # Buscar todos os nomes dos funcionários para o filtro
            cursor.execute("SELECT NOME FROM FUNCIONARIOS ORDER BY NOME")
            todos_funcionarios = [row[0] for row in cursor.fetchall()]

            col1, col2, col3 = st.columns(3)
            with col1:
                funcionarios_selecionados = st.multiselect(
                    "Selecione os Funcionários:", options=todos_funcionarios, default=[]
                )
            with col2:
                data_inicio_filtro = st.date_input("Data de Início", value=None, format="DD/MM/YYYY")
            with col3:
                data_fim_filtro = st.date_input("Data de Fim", value=None, format="DD/MM/YYYY")

            # Construir a cláusula WHERE com base na seleção
            filtros = []
            if funcionarios_selecionados:
                filtro_funcionarios = "(" + ", ".join(f"'{nome}'" for nome in funcionarios_selecionados) + ")"
                filtros.append(f"f.NOME IN {filtro_funcionarios}")
            
            if data_inicio_filtro:
                filtros.append(f"ferias.DATA_INICIO >= '{data_inicio_filtro}'")
            
            if data_fim_filtro:
                filtros.append(f"ferias.DATA_FIM <= '{data_fim_filtro}'")
            
            where_clause = " WHERE " + " AND ".join(filtros) if filtros else ""
            
            query = f"""
                SELECT 
                    f.NOME AS Funcionario,
                    ferias.DATA_INICIO,
                    ferias.DATA_FIM,
                    ferias.REGISTRADO_EM,
                    ferias.ano_referencia
                FROM FERIAS
                JOIN FUNCIONARIOS f ON ferias.FUNCIONARIO_ID = f.ID
                {where_clause}
                ORDER BY 1
            """

            # Executar a query e buscar os registros
            cursor.execute(query)
            registros = cursor.fetchall()

            if registros:
                # Criar o DataFrame para exibir os dados
                df = pd.DataFrame(
                    registros,
                    columns=["Funcionário", "Data de Início", "Data Final", "Aprovado em", "Referência"]
                )

                # Formatando as colunas de data para exibição
                df["Data de Início"] = pd.to_datetime(df["Data de Início"]).dt.strftime("%d/%m/%Y")
                df["Data Final"] = pd.to_datetime(df["Data Final"]).dt.strftime("%d/%m/%Y")
                df["Aprovado em"] = pd.to_datetime(df["Aprovado em"]).dt.strftime("%d/%m/%Y")

                # Exibir o DataFrame no Streamlit
                st.dataframe(df, hide_index=True, use_container_width=True)

            else:
                st.warning("Nenhuma férias marcada no momento.")
        except Exception as e:
            st.error(f"Erro ao buscar férias marcadas: {e}")
    else:
        st.error("Erro na conexão com o banco de dados.")




#Adiconar envento no calendario

def add_evento():

    # Autenticar e obter credenciais para o Google Calendar
    creds = autenticar_google_calendar()
    calendario_id = obter_id_calendario(creds)
    servico = build('calendar', 'v3', credentials=creds)

    st.markdown("<h1 style='text-align: center;'>Agendamento</h1>", unsafe_allow_html=True)

    # Obter lista de funcionários com seus e-mails do banco
    conn = conexao_persistente
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("ROLLBACK")
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




# Iniciar o aplicativo
if __name__ == "__main__":
    tela_inicial()
