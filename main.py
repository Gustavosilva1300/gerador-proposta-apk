import os
import random
import platform
import math
import datetime
import threading
import requests
import matplotlib
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
from fpdf import FPDF
import ssl
import certifi
import shutil
import sqlite3

# Configuração do Kivy
from kivy.config import Config
Config.set('kivy', 'window_icon', 'logo1b.png')

from kivy.lang import Builder
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform as kivy_platform

from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.filemanager import MDFileManager
from kivymd.toast import toast

# Configuração Matplotlib
matplotlib.use('Agg')

# --- FUNÇÃO DE LIMPEZA DE TEXTO (CORREÇÃO DE ACENTOS) ---
def limpar_texto(texto):
    """
    Converte string UTF-8 (Python) para Latin-1 (PDF)
    substituindo caracteres incompatíveis para evitar erros.
    """
    if texto is None: return ""
    if not isinstance(texto, str): texto = str(texto)
    
    substituicoes = {
        '\u2013': '-', '\u2014': '-',   # Travessões
        '\u2018': "'", '\u2019': "'",   # Aspas simples curvas
        '\u201c': '"', '\u201d': '"',   # Aspas duplas curvas
        '²': '2', 'º': 'o', '°': 'o', 'ª': 'a',
        '–': '-'
    }
    
    for old, new in substituicoes.items():
        texto = texto.replace(old, new)

    try:
        # Tenta codificar para latin-1, substituindo erros por '?'
        return texto.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        # Se falhar muito feio, retorna sem acentos básicos (fallback)
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# --- FUNÇÕES DE FORMATAÇÃO (PADRÃO BR) ---
def parse_br(texto):
    if not texto: return 0.0
    try:
        return float(texto.replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0

def fmt_br(valor, casas=2):
    try:
        if valor is None: valor = 0.0
        return f"{valor:,.{casas}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return str(valor)

# --- BANCO DE DADOS ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("solar_database.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.seed_database()

    def seed_database(self):
        # Pré-cadastra os Módulos garantindo que sempre existam
        mods = [
            ("MÓDULO JINKO 725WP BIFACIAL N-TYPE", 725),
            ("MÓDULO LONGI 645WP MONOFACIAL N-TYPE", 645),
            ("MÓDULO TCL 615WP BIFACIAL N-TYPE", 615)
        ]
        for nome, pot in mods:
            self.cursor.execute("SELECT id FROM modulos WHERE nome=?", (nome,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT INTO modulos (nome, potencia) VALUES (?, ?)", (nome, pot))

        # Pré-cadastra os Inversores garantindo que sempre existam
        invs = [
                ("SOLIS ON-GRID 3KW 220V", 3.0, "solar_imagens/solis.png"),
                ("SOLIS ON-GRID 5KW 220V", 5.0, "solar_imagens/solis.png"),
                ("SOLIS ON-GRID 7.5KW 220V", 7.5, "solar_imagens/solis.png"),
                ("SOLIS ON-GRID 10KW 220V", 10.0, "solar_imagens/solis.png"),
                ("SOLIS HIBRIDO 5KW 220V", 5.0, "solar_imagens/solis.png"),
                ("GROWATT ON-GRID 3KW 220V", 3.0, "solar_imagens/growatt.png"),
                ("GROWATT ON-GRID 6KW 220V", 6.0, "solar_imagens/growatt.png"),
                ("GROWATT ON-GRID 10KW 220V", 10.0, "solar_imagens/growatt.png"),
                ("GROWATT ON-GRID 20KW 380V", 20.0, "solar_imagens/growatt.png"),
                ("DEYE HIBRIDO 7.5KW 220V", 7.5, "solar_imagens/deye.png"),
                ("DEYE OFF-GRID 3.6KW 220V", 3.6, "solar_imagens/deye.png"),
                ("FOXESS ON-GRID 6KW 220V", 6.0, "solar_imagens/foxess.png"),
                ("FOXESS ON-GRID 12KW 380V", 12.0, "solar_imagens/foxess.png"),
                ("HUAWEI ON-GRID 5KW 220V", 5.0, "solar_imagens/huawei.png"),
                ("HUAWEI ON-GRID 10KW 220V", 10.0, "solar_imagens/huawei.png"),
                ("SUNGROW ON-GRID 6KW 220V", 6.0, "solar_imagens/sungrow.png"),
                ("SUNGROW ON-GRID 12KW 380V", 12.0, "solar_imagens/sungrow.png"),
                ("LIVOLTEK ON-GRID 6KW 220V", 6.0, "solar_imagens/livoltek.png"),
                ("HOYMILES MICROINVERSOR 2.25KW 220V", 2.25, "solar_imagens/hoymiles.png"),
                ("ENPHASE MICROINVERSOR 0.47KW 220V", 0.475, "solar_imagens/enphase.png"),
                ("NEP MICROINVERSOR 2.25KW", 2.25, "solar_imagens/nep.png")
        ]
        for nome, pot, img in invs:
            self.cursor.execute("SELECT id FROM inversores WHERE nome=?", (nome,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT INTO inversores (nome, potencia_nominal, imagem_path) VALUES (?, ?, ?)", (nome, pot, img))

        # Pré-cadastra as Estruturas garantindo que sempre existam
        ests = [
            ("Laje",),
            ("Solo - Lastro Fortlev Solar",),
            ("Solo Fixo - Estrutura metálica",),
            ("Telhado Ceramico",),
            ("Telhado Fibrocimento - Estrutura em madeira (200mm)",),
            ("Telhado Fibrocimento - Estrutura em madeira (300mm)",),
            ("Telhado Fibrocimento - Estrutura em metal (250mm)",),
            ("Telhado Metálico - Mini trilho (0.5m)",),
            ("Telhado Metálico - Perfil contínuo (2.4m)",),
            ("Telhado Metálico - Perfil contínuo (4.8m)",)
        ]
        for (nome,) in ests:
            self.cursor.execute("SELECT id FROM estruturas WHERE nome=?", (nome,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT INTO estruturas (nome) VALUES (?)", (nome,))
                
        # Pré-cadastra Baterias
        bats = [
            ("BATERIA UCB 100AH (UPLFP48V)", 48, 100),
            ("BATERIA GROWATT AXE 5.0L", 51.2, 100)
        ]
        for nome, tensao, cap in bats:
            self.cursor.execute("SELECT id FROM baterias WHERE nome=?", (nome,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT INTO baterias (nome, tensao, capacidade) VALUES (?, ?, ?)", (nome, tensao, cap))
            
        self.conn.commit()

    def create_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS modulos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, potencia REAL NOT NULL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS inversores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, potencia_nominal REAL NOT NULL, imagem_path TEXT)")
        
        # Adiciona a coluna imagem_path para bancos antigos, caso falte
        try:
            self.cursor.execute("ALTER TABLE inversores ADD COLUMN imagem_path TEXT")
        except:
            pass

        self.cursor.execute("CREATE TABLE IF NOT EXISTS estruturas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS baterias (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, tensao REAL NOT NULL, capacidade REAL NOT NULL)")
        self.conn.commit()

    def check_duplicidade(self, tabela, nome):
        try:
            self.cursor.execute(f"SELECT id FROM {tabela} WHERE nome = ? COLLATE NOCASE", (nome.strip(),))
            return self.cursor.fetchone() is not None
        except: return False

    def add_modulo(self, nome, potencia):
        self.cursor.execute("INSERT INTO modulos (nome, potencia) VALUES (?, ?)", (nome.strip(), potencia))
        self.conn.commit()

    def add_inversor(self, nome, potencia, img_path):
        self.cursor.execute("INSERT INTO inversores (nome, potencia_nominal, imagem_path) VALUES (?, ?, ?)", (nome.strip(), potencia, img_path))
        self.conn.commit()

    def add_estrutura(self, nome):
        self.cursor.execute("INSERT INTO estruturas (nome) VALUES (?)", (nome.strip(),))
        self.conn.commit()

    def get_modulos(self):
        self.cursor.execute("SELECT nome, potencia FROM modulos")
        return self.cursor.fetchall()

    def get_inversores(self):
        self.cursor.execute("SELECT nome, potencia_nominal, imagem_path FROM inversores")
        return self.cursor.fetchall()

    def get_estruturas(self):
        self.cursor.execute("SELECT nome FROM estruturas")
        return self.cursor.fetchall()

    def get_baterias(self):
        self.cursor.execute("SELECT nome, tensao, capacidade FROM baterias")
        return self.cursor.fetchall()

    def update_inversor_image(self, nome, img_path):
        self.cursor.execute("UPDATE inversores SET imagem_path = ? WHERE nome = ?", (img_path, nome.strip()))
        self.conn.commit()

    def delete_item(self, tabela, nome):
        self.cursor.execute(f"DELETE FROM {tabela} WHERE nome = ?", (nome.strip(),))
        self.conn.commit()

    def set_config(self, chave, valor):
        self.cursor.execute("REPLACE INTO config (chave, valor) VALUES (?, ?)", (chave, str(valor)))
        self.conn.commit()

    def get_config(self, chave):
        self.cursor.execute("SELECT valor FROM config WHERE chave=?", (chave,))
        res = self.cursor.fetchone()
        return res[0] if res else None

db = Database()

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        # Tenta carregar imagem se existir
        for img in ["timbrado.png", "timbrado.jpg"]:
            if os.path.exists(img):
                try:
                    self.image(img, x=0, y=0, w=210, h=297)
                    break
                except: pass

    def rounded_rect(self, x, y, w, h, r, style='D'):
        k = self.k; hp = self.h; op = 'S'
        if style == 'F': op = 'f'
        elif style == 'FD' or style == 'DF': op = 'B'
        self._out('%.2f %.2f m' % ((x+r)*k, (hp-y)*k))
        self._out('%.2f %.2f l' % ((x+w-r)*k, (hp-y)*k))
        self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % ((x+w)*k, (hp-y)*k, (x+w)*k, (hp-y-r)*k, (x+w)*k, (hp-y-r)*k))
        self._out('%.2f %.2f l' % ((x+w)*k, (hp-y-h+r)*k))
        self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % ((x+w)*k, (hp-y-h)*k, (x+w-r)*k, (hp-y-h)*k, (x+w-r)*k, (hp-y-h)*k))
        self._out('%.2f %.2f l' % ((x+r)*k, (hp-y-h)*k))
        self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % (x*k, (hp-y-h)*k, x*k, (hp-y-h+r)*k, x*k, (hp-y-h+r)*k))
        self._out('%.2f %.2f l' % (x*k, (hp-y-r)*k))
        self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % (x*k, (hp-y)*k, (x+r)*k, (hp-y)*k, (x+r)*k, (hp-y)*k))
        self._out(op)

    def table_cell(self, label, value, w, h=6, border=1, ln=0, align='L', round_corners=False):
        x_start = self.get_x()
        y_start = self.get_y()
        
        if round_corners: self.rounded_rect(x_start, y_start, w, h, 2)
        else: self.rect(x_start, y_start, w, h)
        
        self.set_xy(x_start + 2, y_start)
        
        # 1. Rótulo (Negrito e Limpo)
        self.set_font("Arial", 'B', 8)
        lbl_str = f"{limpar_texto(str(label))} "
        w_lbl = self.get_string_width(lbl_str)
        self.cell(w_lbl, h, lbl_str, 0, 0, 'L')
        
        # 2. Valor (Normal e Limpo)
        self.set_font("Arial", '', 8)
        val_str = limpar_texto(str(value)).replace('\n', ' ').replace('\r', '') # Previne quebras
        
        # Previne sobreposição horizontal truncando texto que exceda a largura
        max_w = w - w_lbl - 4
        if max_w > 0:
            while len(val_str) > 0 and self.get_string_width(val_str) > max_w:
                val_str = val_str[:-1]
            self.cell(max_w, h, val_str, 0, 0, 'L')
        
        if ln == 1: self.set_xy(self.l_margin, y_start + h)
        else: self.set_xy(x_start + w, y_start)

# --- LAYOUT KV ---
KV = '''
#:set app_bg_color (0.95, 0.95, 0.95, 1)
#:set app_text_color (0.2, 0.2, 0.2, 1)
#:set app_green_color (0, 0.6, 0.2, 1)
#:set card_bg_color (1, 1, 1, 1)

<MDTextField>:
    write_tab: False
    multiline: False
    on_text_validate: self.get_focus_next().focus = True

MDScreen:
    md_bg_color: app_bg_color

    MDBottomNavigation:
        panel_color: (1, 1, 1, 1)
        selected_color_background: (0, 0.6, 0.2, 0.1)
        text_color_active: app_green_color

        # --- ABA 1: CADASTROS ---
        MDBottomNavigationItem:
            id: item_cadastros
            name: 'screen_cadastros'
            text: 'Cadastros'
            icon: 'database-plus'
            
            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "20dp"
                    spacing: "15dp"
                    adaptive_height: True

                    MDLabel:
                        text: "📋 Cadastro de Equipamentos"
                        font_style: "H5"
                        halign: "center"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app_green_color

                    MDLabel:
                        text: "Cadastre os equipamentos que você utiliza nos projetos. Estes dados serão reutilizados nos orçamentos."
                        font_style: "Subtitle2"
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: app_text_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "8dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2
                        
                        MDLabel:
                            text: "PASSO 1: Novo Módulo/Placa"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                            bold: True
                        
                        MDLabel:
                            text: "Descrição: Ex: JinkoSolar 545W, Monocrystalline"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)
                        
                        MDTextField:
                            id: cad_mod_nome
                            hint_text: "Nome do Módulo"
                            mode: "rectangle"
                            line_color_focus: app_green_color
                        
                        MDLabel:
                            text: "Potência em Watts (W): Ex: 545"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)
                        
                        MDTextField:
                            id: cad_mod_pot
                            hint_text: "Potência (W)"
                            mode: "rectangle"
                            line_color_focus: app_green_color
                        
                        MDRaisedButton:
                            text: "✓ Salvar Módulo"
                            size_hint_x: 1
                            md_bg_color: app_green_color
                            on_release: app.salvar_modulo()

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "8dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2
                        
                        MDLabel:
                            text: "PASSO 2: Novo Inversor"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                            bold: True
                        
                        MDLabel:
                            text: "Descrição: Ex: Growatt 10kW, Trifásico"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)
                        
                        MDTextField:
                            id: cad_inv_nome
                            hint_text: "Nome do Inversor"
                            mode: "rectangle"
                            line_color_focus: app_green_color
                        
                        MDLabel:
                            text: "Potência Nominal em kW: Ex: 10"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)
                        
                        MDTextField:
                            id: cad_inv_pot
                            hint_text: "Potência Nominal (kW)"
                            mode: "rectangle"
                            line_color_focus: app_green_color
                        
                        MDLabel:
                            text: "Foto do Equipamento (opcional)"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)
                        
                        MDRaisedButton:
                            text: "📷 Selecionar Foto do Inversor"
                            icon: "image"
                            on_release: app.file_manager_open_cadastro()
                            size_hint_x: 1
                            md_bg_color: (0.4, 0.4, 0.4, 1)
                        
                        MDLabel:
                            id: lbl_inv_img_cad
                            text: "Nenhuma imagem selecionada"
                            font_style: "Caption"
                            halign: "center"
                            theme_text_color: "Custom"
                            text_color: (0.8, 0.4, 0.4, 1)

                        MDRaisedButton:
                            text: "✓ Salvar Inversor"
                            md_bg_color: app_green_color
                            size_hint_x: 1
                            on_release: app.salvar_inversor()

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "8dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2
                        
                        MDLabel:
                            text: "PASSO 3: Nova Estrutura"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                            bold: True
                        
                        MDLabel:
                            text: "Tipo de estrutura para fixação dos painéis: Ex: Telhado Cerâmico, Telha Fibrocimento, Estrutura em Solo"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)
                        
                        MDTextField:
                            id: cad_est_nome
                            hint_text: "Tipo de Estrutura"
                            mode: "rectangle"
                            line_color_focus: app_green_color
                        
                        MDRaisedButton:
                            text: "✓ Salvar Estrutura"
                            md_bg_color: app_green_color
                            size_hint_x: 1
                            on_release: app.salvar_estrutura()

                    MDCard:
                        orientation: "vertical"
                        padding: "10dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2
                        
                        MDLabel:
                            text: "Editar Foto do Inversor"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                        
                        MDTextField:
                            id: edit_inv_nome
                            hint_text: "Selecionar Inversor"
                            readonly: True
                            mode: "rectangle"
                            on_focus: if self.focus: app.abrir_menu_edit_inversor()
                            line_color_focus: app_green_color
                            
                        MDRaisedButton:
                            text: "Selecionar Nova Foto"
                            icon: "image"
                            on_release: app.file_manager_open_edit()
                            size_hint_x: 1
                            md_bg_color: (0.4, 0.4, 0.4, 1)
                        
                        MDLabel:
                            id: lbl_inv_img_edit
                            text: "Nenhuma imagem selecionada"
                            font_style: "Caption"
                            halign: "center"

                        MDRaisedButton:
                            text: "Atualizar Foto"
                            md_bg_color: app_green_color
                            size_hint_x: 1
                            on_release: app.atualizar_inversor()

                    MDCard:
                        orientation: "vertical"
                        padding: "10dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2
                        
                        MDLabel:
                            text: "Remover Equipamento"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: (0.8, 0.2, 0.2, 1)
                        
                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            
                            MDTextField:
                                id: del_categoria
                                hint_text: "Categoria"
                                text: "Módulo"
                                readonly: True
                                mode: "rectangle"
                                size_hint_x: 0.4
                                on_focus: if self.focus: app.menu_del_categoria.open()
                                line_color_focus: (0.8, 0.2, 0.2, 1)
                                
                            MDTextField:
                                id: del_nome
                                hint_text: "Selecionar Item"
                                readonly: True
                                mode: "rectangle"
                                size_hint_x: 0.6
                                on_focus: if self.focus: app.abrir_menu_del_item()
                                line_color_focus: (0.8, 0.2, 0.2, 1)
                                
                        MDRaisedButton:
                            text: "Remover Selecionado"
                            md_bg_color: (0.8, 0.2, 0.2, 1)
                            size_hint_x: 1
                            on_release: app.remover_equipamento()

        # --- ABA 2: ORÇAMENTO ---
        MDBottomNavigationItem:
            id: item_home
            name: 'screen_home'
            text: 'Gerador'
            icon: 'file-document-edit'

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "20dp"
                    spacing: "15dp"
                    adaptive_height: True

                    MDLabel:
                        text: "📊 Gerador de Propostas"
                        font_style: "H5"
                        halign: "center"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app_green_color

                    MDLabel:
                        text: "Preencha os passos abaixo para gerar uma proposta técnica profissional em PDF"
                        font_style: "Subtitle2"
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: app_text_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: (0.95, 1.0, 0.95, 1)
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "PASSO 1️⃣  - Dados do Cliente"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                            bold: True

                        MDLabel:
                            text: "Informações pessoais e endereço do cliente"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)

                        MDTextField:
                            id: nome
                            hint_text: "Nome Completo do Cliente"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDTextField:
                            id: cpf
                            hint_text: "CPF ou CNPJ (somente números)"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: cep
                                hint_text: "CEP (ex: 12345-678)"
                                mode: "rectangle"
                                size_hint_x: 0.7
                                line_color_focus: app_green_color
                                on_text_validate:
                                    app.buscar_cep()
                                    self.get_focus_next().focus = True
                            MDIconButton:
                                icon: "magnify"
                                on_release: app.buscar_cep()
                                pos_hint: {"center_y": .5}
                                theme_text_color: "Custom"
                                icon_size: "28sp"

                        MDTextField:
                            id: logradouro
                            hint_text: "Rua/Alameda"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: numero
                                hint_text: "Número"
                                mode: "rectangle"
                                size_hint_x: 0.4
                                line_color_focus: app_green_color
                            MDTextField:
                                id: complemento
                                hint_text: "Complemento (apto, sala, etc)"
                                mode: "rectangle"
                                size_hint_x: 0.6
                                line_color_focus: app_green_color

                        MDTextField:
                            id: bairro
                            hint_text: "Bairro"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: cidade
                                hint_text: "Cidade"
                                mode: "rectangle"
                                size_hint_x: 0.7
                                line_color_focus: app_green_color
                            MDTextField:
                                id: estado
                                hint_text: "UF (MG, SP...)"
                                mode: "rectangle"
                                size_hint_x: 0.3
                                on_focus: if self.focus: app.menu_estados.open()
                                line_color_focus: app_green_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: (0.95, 0.98, 1.0, 1)
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "PASSO 2️⃣  - Localização (Irradiação Solar)"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: (0, 0.4, 0.8, 1)
                            bold: True

                        MDLabel:
                            text: "Buscar dados de irradiação solar (HSP) da NASA baseado na localização"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDRaisedButton:
                                text: "🔍 Buscar Irradiação"
                                on_release: app.buscar_solar()
                                pos_hint: {"center_y": .5}
                                md_bg_color: (0, 0.4, 0.8, 1)
                            MDTextField:
                                id: hsp
                                hint_text: "HSP (kWh/m²/dia)"
                                text: "5,1"
                                readonly: True
                                mode: "rectangle"
                                line_color_focus: (0, 0.4, 0.8, 1)

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: (1.0, 0.98, 0.95, 1)
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "PASSO 3️⃣  - Consumo Energético"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: (0.8, 0.4, 0, 1)
                            bold: True

                        MDLabel:
                            text: "Defina a meta de geração de energia baseado no consumo"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)

                        MDLabel:
                            text: "Meta de Geração (kWh/mês): Ex: 1200"
                            font_style: "Subtitle2"
                            theme_text_color: "Custom"
                            text_color: (0.3, 0.3, 0.3, 1)

                        MDTextField:
                            id: meta_geracao
                            hint_text: "Digite a meta em kWh"
                            mode: "rectangle"
                            line_color_focus: (0.8, 0.4, 0, 1)

                        MDRaisedButton:
                            text: "🧮 CALCULAR KIT SUGERIDO"
                            on_release: app.calcular_sugestao()
                            size_hint_x: 1
                            md_bg_color: (0.8, 0.4, 0, 1)
                            elevation: 3

                        MDCard:
                            orientation: "vertical"
                            padding: "12dp"
                            size_hint_y: None
                            height: "100dp"
                            md_bg_color: (1.0, 1.0, 0.9, 1)
                            radius: [8]
                            elevation: 1
                            MDLabel:
                                id: lbl_resultado_kwp
                                text: "Potência: 0,00 kWp"
                                halign: "center"
                                font_style: "H6"
                                theme_text_color: "Custom"
                                text_color: (0.8, 0.4, 0, 1)
                                bold: True
                            MDLabel:
                                id: lbl_consumo_usado
                                text: "Consumo Base: 0 kWh/mês"
                                halign: "center"
                                font_style: "Subtitle1"
                                theme_text_color: "Custom"
                                text_color: (0.3, 0.3, 0.3, 1)

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: (0.98, 0.95, 1.0, 1)
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "PASSO 4️⃣  - Custos e Tarifas"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: (0.6, 0.2, 0.8, 1)
                            bold: True

                        MDLabel:
                            text: "Informações financeiras do projeto"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: valor_kwh
                                hint_text: "Valor kWh (R$)"
                                text: "1,16"
                                mode: "rectangle"
                                line_color_focus: (0.6, 0.2, 0.8, 1)
                            MDTextField:
                                id: custo_equip
                                hint_text: "Custo do Kit (R$)"
                                text: "0"
                                mode: "rectangle"
                                line_color_focus: (0.6, 0.2, 0.8, 1)

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: mao_obra
                                hint_text: "Mão de Obra (R$)"
                                text: "0"
                                mode: "rectangle"
                                line_color_focus: (0.6, 0.2, 0.8, 1)
                            MDTextField:
                                id: classificacao
                                hint_text: "Classificação (ex: Residencial)"
                                text: "Residencial"
                                mode: "rectangle"
                                line_color_focus: (0.6, 0.2, 0.8, 1)

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: (0.95, 1.0, 0.98, 1)
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "PASSO 5️⃣  - Configuração do Kit"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: (0.2, 0.6, 0.6, 1)
                            bold: True

                        MDLabel:
                            text: "Selecione os equipamentos do seu projeto"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)

                        MDLabel:
                            text: "Módulos Solares:"
                            font_style: "Subtitle2"
                            bold: True
                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: qtd_modulos
                                hint_text: "Qtd"
                                text: "0"
                                size_hint_x: 0.2
                                mode: "rectangle"
                                line_color_focus: (0.2, 0.6, 0.6, 1)
                            MDTextField:
                                id: nome_modulo
                                hint_text: "Clique para selecionar"
                                text: "Selecione..."
                                readonly: True
                                size_hint_x: 0.8
                                mode: "rectangle"
                                on_focus: if self.focus: app.abrir_menu_modulos()
                                line_color_focus: (0.2, 0.6, 0.6, 1)

                        MDLabel:
                            text: "Inversor:"
                            font_style: "Subtitle2"
                            bold: True
                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: qtd_inversor
                                hint_text: "Qtd"
                                text: "1"
                                size_hint_x: 0.2
                                mode: "rectangle"
                                line_color_focus: (0.2, 0.6, 0.6, 1)
                            MDTextField:
                                id: nome_inversor
                                hint_text: "Clique para selecionar"
                                text: "Selecione..."
                                readonly: True
                                size_hint_x: 0.8
                                mode: "rectangle"
                                on_focus: if self.focus: app.abrir_menu_inversores()
                                line_color_focus: (0.2, 0.6, 0.6, 1)

                        MDLabel:
                            text: "Estrutura de Fixação:"
                            font_style: "Subtitle2"
                            bold: True
                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: qtd_estrutura
                                hint_text: "Qtd"
                                text: "4"
                                size_hint_x: 0.2
                                mode: "rectangle"
                                line_color_focus: (0.2, 0.6, 0.6, 1)
                            MDTextField:
                                id: nome_estrutura
                                hint_text: "Clique para selecionar"
                                text: "Selecione..."
                                size_hint_x: 0.8
                                readonly: True
                                mode: "rectangle"
                                on_focus: if self.focus: app.abrir_menu_estruturas()
                                line_color_focus: (0.2, 0.6, 0.6, 1)

                        MDLabel:
                            text: "Cabos e Conectores:"
                            font_style: "Subtitle2"
                            bold: True
                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: qtd_cabo
                                hint_text: "Metros"
                                text: "50"
                                size_hint_x: 0.5
                                mode: "rectangle"
                                line_color_focus: (0.2, 0.6, 0.6, 1)
                            MDTextField:
                                id: qtd_conectores
                                hint_text: "Pares MC4"
                                text: "4"
                                size_hint_x: 0.5
                                mode: "rectangle"
                                line_color_focus: (0.2, 0.6, 0.6, 1)

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: (0.9, 1, 0.9, 1)
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "✅ FINALIZAR - Gerar Proposta"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                            bold: True

                        MDLabel:
                            text: "Clique abaixo para gerar o PDF da proposta técnica"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: (0.5, 0.5, 0.5, 1)

                        MDRaisedButton:
                            text: "📄 GERAR PDF FINAL"
                            md_bg_color: app_green_color
                            font_size: "18sp"
                            size_hint_x: 1
                            elevation: 3
                            on_release: app.preparar_pdf()
                    
                    Widget:
                        size_hint_y: None
                        height: "30dp"

        # --- ABA 3: HÍBRIDO ---
        MDBottomNavigationItem:
            name: 'screen_hibrido'
            text: 'Híbrido'
            icon: 'battery-charging-100'

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "20dp"
                    spacing: "15dp"
                    adaptive_height: True

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "1. Dados do Cliente"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color

                        MDTextField:
                            id: hib_nome
                            hint_text: "Nome Completo"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDTextField:
                            id: hib_cpf
                            hint_text: "CPF/CNPJ"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_cep
                                hint_text: "CEP"
                                mode: "rectangle"
                                size_hint_x: 0.7
                                line_color_focus: app_green_color
                                on_text_validate:
                                    app.buscar_cep('hib_')
                                    self.get_focus_next().focus = True
                            MDIconButton:
                                icon: "magnify"
                                on_release: app.buscar_cep('hib_')
                                pos_hint: {"center_y": .5}

                        MDTextField:
                            id: hib_logradouro
                            hint_text: "Rua/Alameda"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_numero
                                hint_text: "Número"
                                mode: "rectangle"
                                size_hint_x: 0.4
                                line_color_focus: app_green_color
                            MDTextField:
                                id: hib_complemento
                                hint_text: "Complemento"
                                mode: "rectangle"
                                size_hint_x: 0.6
                                line_color_focus: app_green_color

                        MDTextField:
                            id: hib_bairro
                            hint_text: "Bairro"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDTextField:
                            id: hib_cidade
                            hint_text: "Cidade"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDTextField:
                            id: hib_estado
                            hint_text: "Estado (UF)"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDTextField:
                            id: hib_classificacao
                            hint_text: "Classificação"
                            text: "Residencial"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "2. Dados Técnicos (NASA)"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDRaisedButton:
                                text: "Buscar Irradiação"
                                on_release: app.buscar_solar('hib_')
                                pos_hint: {"center_y": .5}
                                md_bg_color: app_green_color
                            MDTextField:
                                id: hib_hsp
                                hint_text: "HSP (Média)"
                                text: "5,1"
                                readonly: True
                                mode: "rectangle"
                                line_color_focus: app_green_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "3. Dimensionamento Geração"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                        
                        MDLabel:
                            text: "Opção A: Histórico 12 Meses"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: app_text_color
                        
                        MDGridLayout:
                            cols: 3
                            adaptive_height: True
                            spacing: "10dp"
                            
                            MDTextField:
                                id: hib_mes_1
                                hint_text: "Jan"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_2
                                hint_text: "Fev"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_3
                                hint_text: "Mar"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_4
                                hint_text: "Abr"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_5
                                hint_text: "Mai"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_6
                                hint_text: "Jun"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_7
                                hint_text: "Jul"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_8
                                hint_text: "Ago"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_9
                                hint_text: "Set"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_10
                                hint_text: "Out"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_11
                                hint_text: "Nov"
                                mode: "rectangle"
                            MDTextField:
                                id: hib_mes_12
                                hint_text: "Dez"
                                mode: "rectangle"

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "20dp"
                            adaptive_height: True
                            MDLabel:
                                text: "Aumento de Carga?"
                                pos_hint: {"center_y": .5}
                                size_hint_x: 0.6
                            MDSwitch:
                                id: hib_switch_aumento
                                active: False
                                pos_hint: {"center_y": .5}
                                on_active: app.toggle_aumento(*args, prefix='hib_')
                                thumb_color_active: app_green_color

                        MDTextField:
                            id: hib_valor_aumento
                            hint_text: "Valor Adicional (kWh)"
                            text: "0"
                            mode: "rectangle"
                            disabled: True
                            opacity: 0.5
                            line_color_focus: app_green_color

                        MDLabel:
                            text: "OU"
                            halign: "center"
                            font_style: "H6"

                        MDLabel:
                            text: "Opção B: Meta Manual"
                            font_style: "Caption"

                        MDTextField:
                            id: hib_meta_geracao
                            hint_text: "Meta de Geração (kWh)"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                        MDRaisedButton:
                            text: "CALCULAR KIT SUGERIDO"
                            on_release: app.calcular_sugestao('hib_')
                            size_hint_x: 1
                            md_bg_color: app_green_color
                            elevation: 3

                        MDCard:
                            orientation: "vertical"
                            padding: "10dp"
                            size_hint_y: None
                            height: "80dp"
                            md_bg_color: (0.9, 1, 0.9, 1)
                            radius: [10]
                            elevation: 2
                            MDLabel:
                                id: hib_lbl_resultado_kwp
                                text: "Potência: 0,00 kWp"
                                halign: "center"
                                font_style: "H6"
                                theme_text_color: "Custom"
                                text_color: app_green_color
                            MDLabel:
                                id: hib_lbl_consumo_usado
                                text: "Consumo Base: 0 kWh"
                                halign: "center"
                                font_style: "Caption"

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "3. Especificações do Banco de Baterias"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            
                            MDTextField:
                                id: hib_tensao_banco
                                hint_text: "Tensão do Banco (V)"
                                mode: "rectangle"
                                line_color_focus: app_green_color
                                
                            MDTextField:
                                id: hib_capacidade_bateria
                                hint_text: "Capacidade da Bateria (Ah)"
                                mode: "rectangle"
                                line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            
                            MDTextField:
                                id: hib_dod
                                hint_text: "DoD Máxima (%)"
                                text: "80"
                                mode: "rectangle"
                                line_color_focus: app_green_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "5. Preços e Custos"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_valor_kwh
                                hint_text: "Valor kWh (R$)"
                                text: "1,16"
                                mode: "rectangle"
                                line_color_focus: app_green_color
                            MDIconButton:
                                icon: "web"
                                on_release: app.buscar_tarifa_cemig('hib_')
                                pos_hint: {"center_y": .5}

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_custo_equip
                                hint_text: "Custo Equip. (R$)"
                                text: "0"
                                mode: "rectangle"
                                line_color_focus: app_green_color
                            MDTextField:
                                id: hib_mao_obra
                                hint_text: "Mão de Obra (R$)"
                                text: "0"
                                mode: "rectangle"
                                line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_custo_baterias
                                hint_text: "Custo Baterias (R$)"
                                text: "0"
                                mode: "rectangle"
                                line_color_focus: app_green_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "4. Dimensionamento Backup"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color

                        MDTextField:
                            id: hib_consumo_critico
                            hint_text: "Consumo Crítico do Backup (kWh/dia)"
                            mode: "rectangle"
                            line_color_focus: app_green_color

                    MDCard:
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "10dp"
                        adaptive_height: True
                        md_bg_color: card_bg_color
                        radius: [10]
                        elevation: 2

                        MDLabel:
                            text: "6. Configuração do Kit"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_qtd_modulos
                                hint_text: "Qtd"
                                text: "0"
                                size_hint_x: 0.2
                                mode: "rectangle"
                                line_color_focus: app_green_color
                            MDTextField:
                                id: hib_nome_modulo
                                hint_text: "Selecionar Módulo"
                                text: "Selecione..."
                                readonly: True
                                size_hint_x: 0.8
                                mode: "rectangle"
                                on_focus: if self.focus: app.abrir_menu_modulos('hib_')
                                line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_qtd_inversor
                                hint_text: "Qtd"
                                text: "1"
                                size_hint_x: 0.2
                                mode: "rectangle"
                                line_color_focus: app_green_color
                            MDTextField:
                                id: hib_sel_inversor
                                hint_text: "Selecionar Inversor Híbrido"
                                readonly: True
                                size_hint_x: 0.8
                                mode: "rectangle"
                                on_focus: if self.focus: app.abrir_menu_inversores_hib()
                                line_color_focus: app_green_color

                        MDTextField:
                            id: hib_sel_bateria
                            hint_text: "Selecionar Bateria Cadastrada"
                            readonly: True
                            mode: "rectangle"
                            on_focus: if self.focus: app.abrir_menu_baterias()
                            line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_qtd_estrutura
                                hint_text: "Qtd"
                                text: "4"
                                size_hint_x: 0.2
                                mode: "rectangle"
                                line_color_focus: app_green_color
                            MDTextField:
                                id: hib_nome_estrutura
                                hint_text: "Selecionar Estrutura"
                                text: "PERFIS DE ALUMÍNIO"
                                size_hint_x: 0.8
                                readonly: True
                                mode: "rectangle"
                                on_focus: if self.focus: app.abrir_menu_estruturas('hib_')
                                line_color_focus: app_green_color

                        MDBoxLayout:
                            orientation: "horizontal"
                            spacing: "10dp"
                            adaptive_height: True
                            MDTextField:
                                id: hib_qtd_cabo
                                hint_text: "Metros"
                                text: "50"
                                size_hint_x: 0.2
                                mode: "rectangle"
                                line_color_focus: app_green_color
                            MDTextField:
                                id: hib_qtd_conectores
                                hint_text: "Pares MC4"
                                text: "4"
                                size_hint_x: 0.8
                                mode: "rectangle"
                                line_color_focus: app_green_color

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: "10dp"
                        adaptive_height: True

                        MDRaisedButton:
                            text: "LIMPAR"
                            md_bg_color: (0.5, 0.5, 0.5, 1)
                            font_size: "16sp"
                            size_hint_x: 0.3
                            elevation: 3
                            on_release: app.limpar_hibrido()

                        MDRaisedButton:
                            text: "CALCULAR BACKUP"
                            md_bg_color: app_green_color
                            font_size: "16sp"
                            size_hint_x: 0.7
                            elevation: 3
                            on_release: app.calcular_orcamento_hibrido()

                    MDCard:
                        id: hib_resultado_card
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "8dp"
                        adaptive_height: True
                        md_bg_color: (0.9, 1, 0.9, 1)
                        radius: [10]
                        elevation: 2
                        opacity: 0
                        disabled: True
                        
                        MDLabel:
                            text: "Resultados do Dimensionamento"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                            halign: "center"
                            bold: True
                        MDSeparator:
                            height: "1dp"
                        MDLabel:
                            id: hib_res_capacidade
                            text: "Capacidade Total: 0.00 kWh"
                        MDLabel:
                            id: hib_res_util
                            text: "Energia Útil: 0.00 kWh"
                        MDLabel:
                            id: hib_res_autonomia
                            text: "Autonomia: 0.0 dias (0 horas)"
                        MDLabel:
                            id: hib_res_kit
                            text: "Kit Solar: 0,00 kWp (0 Painéis e 1 Inversor)"
                        MDSeparator:
                            height: "1dp"
                        MDLabel:
                            id: hib_res_preco
                            text: "Preço Final de Venda: R$ 0,00"
                            font_style: "H6"
                            theme_text_color: "Custom"
                            text_color: app_green_color
                            halign: "center"
                            bold: True

                    MDRaisedButton:
                        text: "GERAR PDF HÍBRIDO"
                        md_bg_color: app_green_color
                        font_size: "18sp"
                        size_hint_x: 1
                        elevation: 3
                        on_release: app.preparar_pdf_hibrido()

                    Widget:
                        size_hint_y: None
                        height: "50dp"

        # --- ABA 4: CONFIGURAÇÕES ---
        MDBottomNavigationItem:
            id: item_config
            name: 'screen_config'
            text: 'Ajustes'
            icon: 'cog'

            MDBoxLayout:
                orientation: "vertical"
                padding: "20dp"
                spacing: "20dp"
                pos_hint: {"center_y": .5}
                adaptive_height: True

                MDLabel:
                    text: "⚙️ Configurações do Sistema"
                    font_style: "H5"
                    halign: "center"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app_green_color

                MDCard:
                    orientation: "vertical"
                    padding: "20dp"
                    spacing: "15dp"
                    adaptive_height: True
                    md_bg_color: card_bg_color
                    radius: [10]
                    elevation: 2

                    MDLabel:
                        text: "Numeração das Propostas"
                        font_style: "Subtitle1"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app_green_color

                    MDLabel:
                        text: "Define o número inicial para as próximas propostas que serão geradas"
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: (0.5, 0.5, 0.5, 1)

                    MDTextField:
                        id: config_num_prop
                        hint_text: "Próximo Nº da Proposta"
                        text: "100"
                        input_filter: "int"
                        mode: "rectangle"
                        line_color_focus: app_green_color

                    MDRaisedButton:
                        text: "💾 SALVAR NÚMERO"
                        size_hint_x: 1
                        md_bg_color: app_green_color
                        on_release: app.salvar_num_proposta()

                MDSeparator:
                    height: "2dp"

                MDCard:
                    orientation: "vertical"
                    padding: "20dp"
                    spacing: "15dp"
                    adaptive_height: True
                    md_bg_color: card_bg_color
                    radius: [10]
                    elevation: 2

                    MDLabel:
                        text: "Diretório de Salvamento"
                        font_style: "Subtitle1"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app_green_color

                    MDLabel:
                        text: "Escolha onde deseja salvar os arquivos PDF das propostas"
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: (0.5, 0.5, 0.5, 1)

                    MDTextField:
                        id: config_pdf_path
                        hint_text: "Caminho da Pasta"
                        text: "Padrão (Downloads)"
                        mode: "rectangle"
                        readonly: True
                        line_color_focus: app_green_color

                    MDRaisedButton:
                        text: "📁 SELECIONAR PASTA"
                        icon: "folder"
                        size_hint_x: 1
                        md_bg_color: (0.4, 0.4, 0.4, 1)
                        on_release: app.file_manager_open_dir()
'''

class SolarApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Green"
        
        # Força o ícone do aplicativo (Janela e Barra de Tarefas)
        self.icon = 'logo1b.png'
        Window.icon = 'logo1b.png'
        
        # Evita que a janela abra muito pequena e esprema os textos
        Window.minimum_width = 700
        Window.minimum_height = 600
        if Window.width < 700: Window.size = (800, 800)
        
        # Aumenta os espaçamentos dinamicamente para os campos não sobreporem
        global KV
        KV = KV.replace('spacing: "8dp"', 'spacing: "20dp"')
        KV = KV.replace('spacing: "10dp"', 'spacing: "20dp"')
            
        return Builder.load_string(KV)

    def on_start(self):
        self.img_folder = "solar_imagens"
        if not os.path.exists(self.img_folder): os.makedirs(self.img_folder)
        self.irradiacao_mensal = [5.1] * 12
        self.consumo_final_usado = 0.0
        self.consumo_final_usado_hib = 0.0
        self.lat = ""
        self.lon = ""
        self.img_inversor_orcamento = None 
        self.img_inversor_hibrido = None
        self.temp_img_cadastro = None
        self.temp_img_edit = None

        # Carregar configurações
        last_prop = db.get_config('num_proposta')
        self.root.ids.config_num_prop.text = str(last_prop) if last_prop else "100"

        saved_pdf_path = db.get_config('pdf_path')
        if saved_pdf_path and os.path.exists(saved_pdf_path):
            self.root.ids.config_pdf_path.text = saved_pdf_path

        estados = ["MG", "SP", "RJ", "ES", "BA", "DF", "GO", "RS", "SC", "PR", "PE", "CE"]
        self.menu_estados = MDDropdownMenu(
            caller=self.root.ids.estado,
            items=[{"viewclass": "OneLineListItem", "text": i, "on_release": lambda x=i: self.set_item(self.root.ids.estado, x, "estado")} for i in estados],
            width_mult=4,
        )
        
        categorias_del = ["Módulo", "Inversor", "Estrutura"]
        self.menu_del_categoria = MDDropdownMenu(
            caller=self.root.ids.del_categoria,
            items=[{"viewclass": "OneLineListItem", "text": i, "on_release": lambda x=i: self.set_item(self.root.ids.del_categoria, x, "del_cat")} for i in categorias_del],
            width_mult=4,
        )
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path,
            preview=True,
        )
        self.file_manager_mode = "file"

    def set_item(self, text_item, text_value, type_menu):
        text_item.text = text_value
        if type_menu == "estado": 
            self.menu_estados.dismiss()
        elif type_menu == "del_cat":
            self.menu_del_categoria.dismiss()

    def toggle_aumento(self, checkbox, value, prefix=""):
        if value:
            self.root.ids[prefix + 'valor_aumento'].disabled = False
            self.root.ids[prefix + 'valor_aumento'].opacity = 1
        else:
            self.root.ids[prefix + 'valor_aumento'].disabled = True
            self.root.ids[prefix + 'valor_aumento'].opacity = 0.5
            self.root.ids[prefix + 'valor_aumento'].text = "0"

    # --- GERENCIADOR DE ARQUIVOS ---
    def file_manager_open_cadastro(self):
        self.file_manager_mode = "file"
        path = os.path.expanduser("~")
        if kivy_platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            path = "/storage/emulated/0/"
        self.file_manager.show(path)

    def file_manager_open_edit(self):
        self.file_manager_mode = "file_edit"
        path = os.path.expanduser("~")
        if kivy_platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            path = "/storage/emulated/0/"
        self.file_manager.show(path)

    def file_manager_open_dir(self):
        self.file_manager_mode = "dir"
        path = os.path.expanduser("~")
        if kivy_platform == "android":
            path = "/storage/emulated/0/"
        self.file_manager.show(path)

    def select_path(self, path):
        self.exit_manager()
        
        if self.file_manager_mode == "file":
            self.temp_img_cadastro = path
            self.root.ids.lbl_inv_img_cad.text = f"Selecionado: {os.path.basename(path)}"
            toast("Imagem selecionada!")
            
        elif self.file_manager_mode == "file_edit":
            self.temp_img_edit = path
            self.root.ids.lbl_inv_img_edit.text = f"Selecionado: {os.path.basename(path)}"
            toast("Nova imagem selecionada!")
            
        elif self.file_manager_mode == "dir":
            final_dir = os.path.dirname(path) if os.path.isfile(path) else path
            self.root.ids.config_pdf_path.text = final_dir
            db.set_config('pdf_path', final_dir)
            toast(f"Pasta salva: {os.path.basename(final_dir)}")

    def exit_manager(self, *args):
        self.file_manager.close()

    # --- SALVAR ITENS ---
    def salvar_modulo(self):
        nome = self.root.ids.cad_mod_nome.text
        pot = parse_br(self.root.ids.cad_mod_pot.text)
        if nome and pot:
            if db.check_duplicidade("modulos", nome):
                toast("Erro: Módulo já cadastrado!")
                return
            db.add_modulo(nome, pot)
            toast("Módulo Salvo!")
            self.root.ids.cad_mod_nome.text = ""
            self.root.ids.cad_mod_pot.text = ""
        else: toast("Preencha todos os campos")

    def salvar_inversor(self):
        nome = self.root.ids.cad_inv_nome.text
        pot = parse_br(self.root.ids.cad_inv_pot.text)
        if nome and pot:
            if db.check_duplicidade("inversores", nome):
                toast("Erro: Inversor já cadastrado!")
                return
            final_path = ""
            if self.temp_img_cadastro:
                ext = os.path.splitext(self.temp_img_cadastro)[1]
                filename = f"inv_{random.randint(1000,9999)}{ext}"
                final_path = os.path.join(self.img_folder, filename)
                try: shutil.copy(self.temp_img_cadastro, final_path)
                except: toast("Erro ao copiar imagem")
            db.add_inversor(nome, pot, final_path)
            toast("Inversor Salvo com Sucesso!")
            self.root.ids.cad_inv_nome.text = ""
            self.root.ids.cad_inv_pot.text = ""
            self.root.ids.lbl_inv_img_cad.text = "Nenhuma imagem"
            self.temp_img_cadastro = None
        else: toast("Preencha nome e potência")

    def salvar_estrutura(self):
        nome = self.root.ids.cad_est_nome.text
        if nome:
            if db.check_duplicidade("estruturas", nome):
                toast("Erro: Estrutura já cadastrada!")
                return
            db.add_estrutura(nome)
            toast("Estrutura Salva!")
            self.root.ids.cad_est_nome.text = ""
        else:
            toast("Preencha o nome da estrutura")

    def atualizar_inversor(self):
        nome = self.root.ids.edit_inv_nome.text
        if nome and self.temp_img_edit:
            ext = os.path.splitext(self.temp_img_edit)[1]
            filename = f"inv_{random.randint(1000,9999)}{ext}"
            final_path = os.path.join(self.img_folder, filename)
            try: shutil.copy(self.temp_img_edit, final_path)
            except: toast("Erro ao copiar imagem")
            
            db.update_inversor_image(nome, final_path)
            toast("Foto Atualizada com Sucesso!")
            self.root.ids.edit_inv_nome.text = ""
            self.root.ids.lbl_inv_img_edit.text = "Nenhuma imagem"
            self.temp_img_edit = None
        else: toast("Selecione um inversor e uma nova foto!")

    def salvar_num_proposta(self):
        num = self.root.ids.config_num_prop.text
        if num and num.isdigit():
            db.set_config('num_proposta', num)
            toast("Número da proposta salvo!")
        else:
            toast("Digite um número válido")

    def abrir_menu_del_item(self):
        categoria = self.root.ids.del_categoria.text
        menu_items = []
        if categoria == "Módulo":
            for nome, pot in db.get_modulos():
                menu_items.append({"viewclass": "OneLineListItem", "text": nome, "on_release": lambda x=nome: self.set_del_item(x)})
        elif categoria == "Inversor":
            for nome, pot, img in db.get_inversores():
                menu_items.append({"viewclass": "OneLineListItem", "text": nome, "on_release": lambda x=nome: self.set_del_item(x)})
        elif categoria == "Estrutura":
            for (nome,) in db.get_estruturas():
                menu_items.append({"viewclass": "OneLineListItem", "text": nome, "on_release": lambda x=nome: self.set_del_item(x)})
        
        if not menu_items: toast("Nenhum item cadastrado!"); return
            
        self.menu_del_item = MDDropdownMenu(caller=self.root.ids.del_nome, items=menu_items, width_mult=8)
        self.menu_del_item.open()

    def set_del_item(self, text):
        self.root.ids.del_nome.text = text
        self.menu_del_item.dismiss()

    def remover_equipamento(self):
        categoria = self.root.ids.del_categoria.text
        nome = self.root.ids.del_nome.text
        if not nome: toast("Selecione um item para remover!"); return
            
        if categoria == "Módulo": db.delete_item("modulos", nome)
        elif categoria == "Inversor": db.delete_item("inversores", nome)
        elif categoria == "Estrutura": db.delete_item("estruturas", nome)
            
        toast(f"Equipamento removido!")
        self.root.ids.del_nome.text = ""

    # --- MENUS ---
    def abrir_menu_modulos(self, prefix=""):
        items_db = db.get_modulos()
        if not items_db: toast("Nenhum módulo cadastrado!"); return
        menu_items = []
        for nome, pot in items_db:
            txt = f"{nome} ({fmt_br(pot, 0)}W)"
            menu_items.append({"viewclass": "OneLineListItem", "text": txt, "on_release": lambda x=txt, p=pot: self.set_modulo_choice(x, p, prefix)})
        self.menu_modulos = MDDropdownMenu(caller=self.root.ids[prefix + 'nome_modulo'], items=menu_items, width_mult=8)
        self.menu_modulos.open()

    def set_modulo_choice(self, text, potencia_w, prefix=""):
        self.root.ids[prefix + 'nome_modulo'].text = text
        self.menu_modulos.dismiss()
        self.atualizar_potencia_kit(prefix)

    def atualizar_potencia_kit(self, prefix=""):
        ids = self.root.ids
        qtd_str = ids[prefix + 'qtd_modulos'].text
        nome_mod = ids[prefix + 'nome_modulo'].text
        
        try: qtd = int(qtd_str)
        except: qtd = 0
            
        pot_modulo_w = 0.0
        for n, p in db.get_modulos():
            if nome_mod and nome_mod.startswith(n):
                pot_modulo_w = float(p)
                break
                
        pot_total_kwp = (qtd * pot_modulo_w) / 1000.0
        
        lbl_id = prefix + 'lbl_potencia_total'
        if lbl_id in ids:
            ids[lbl_id].text = f"Potência do Kit: {fmt_br(pot_total_kwp, 2)} kWp"

    def abrir_menu_inversores(self):
        items_db = db.get_inversores()
        if not items_db: toast("Nenhum inversor cadastrado!"); return
        menu_items = []
        for nome, pot, img_path in items_db:
            txt = f"{nome} ({fmt_br(pot, 1)}kW)"
            menu_items.append({"viewclass": "OneLineListItem", "text": txt, "on_release": lambda x=txt, p=img_path: self.set_inversor_choice(x, p)})
        self.menu_inversores = MDDropdownMenu(caller=self.root.ids.nome_inversor, items=menu_items, width_mult=8)
        self.menu_inversores.open()

    def set_inversor_choice(self, text, img_path):
        self.root.ids.nome_inversor.text = text
        self.img_inversor_orcamento = img_path
        self.menu_inversores.dismiss()
        
    def abrir_menu_edit_inversor(self):
        items_db = db.get_inversores()
        if not items_db: toast("Nenhum inversor cadastrado!"); return
        menu_items = [{"viewclass": "OneLineListItem", "text": n, "on_release": lambda x=n: self.set_edit_inversor_choice(x)} for n, p, i in items_db]
        self.menu_edit_inv = MDDropdownMenu(caller=self.root.ids.edit_inv_nome, items=menu_items, width_mult=8)
        self.menu_edit_inv.open()

    def set_edit_inversor_choice(self, text):
        self.root.ids.edit_inv_nome.text = text
        self.menu_edit_inv.dismiss()

    def abrir_menu_estruturas(self, prefix=""):
        items_db = db.get_estruturas()
        if not items_db: toast("Nenhuma estrutura cadastrada!"); return
        menu_items = []
        for (nome,) in items_db:
            menu_items.append({"viewclass": "OneLineListItem", "text": nome, "on_release": lambda x=nome: self.set_estrutura_choice(x, prefix)})
        self.menu_estruturas = MDDropdownMenu(caller=self.root.ids[prefix + 'nome_estrutura'], items=menu_items, width_mult=8)
        self.menu_estruturas.open()

    def set_estrutura_choice(self, text, prefix=""):
        self.root.ids[prefix + 'nome_estrutura'].text = text
        self.menu_estruturas.dismiss()
        
    def abrir_menu_baterias(self):
        items_db = db.get_baterias()
        if not items_db: toast("Nenhuma bateria cadastrada!"); return
        menu_items = [{"viewclass": "OneLineListItem", "text": n, "on_release": lambda x=n, t=ten, c=cap: self.set_bateria_choice(x, t, c)} for n, ten, cap in items_db]
        self.menu_baterias = MDDropdownMenu(caller=self.root.ids.hib_sel_bateria, items=menu_items, width_mult=8)
        self.menu_baterias.open()

    def set_bateria_choice(self, text, tensao, cap):
        self.root.ids.hib_sel_bateria.text = text
        self.root.ids.hib_tensao_banco.text = str(tensao)
        self.root.ids.hib_capacidade_bateria.text = str(cap)
        self.menu_baterias.dismiss()

    def abrir_menu_inversores_hib(self):
        items_db = db.get_inversores()
        if not items_db: toast("Nenhum inversor cadastrado!"); return
        menu_items = [{"viewclass": "OneLineListItem", "text": f"{n} ({fmt_br(p, 1)}kW)", "on_release": lambda x=f"{n} ({fmt_br(p, 1)}kW)", pt=p, img=i: self.set_inversor_hib_choice(x, pt, img)} for n, p, i in items_db]
        self.menu_inversores_hib = MDDropdownMenu(caller=self.root.ids.hib_sel_inversor, items=menu_items, width_mult=8)
        self.menu_inversores_hib.open()

    def set_inversor_hib_choice(self, text, pot, img_path):
        self.root.ids.hib_sel_inversor.text = text
        self.img_inversor_hibrido = img_path
        self.menu_inversores_hib.dismiss()

    # --- LÓGICA E PDF ---
    def buscar_cep(self, prefix=""):
        cep = self.root.ids[prefix + 'cep'].text.replace("-", "").strip()
        if len(cep) != 8: toast("CEP Inválido"); return
        def run():
            try:
                res = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5)
                if res.status_code == 200 and "erro" not in res.json():
                    data = res.json()
                    Clock.schedule_once(lambda dt: self.preencher_end(data, prefix))
                else: Clock.schedule_once(lambda dt: toast("CEP não encontrado"))
            except: Clock.schedule_once(lambda dt: toast("Erro de conexão"))
        threading.Thread(target=run).start()

    def preencher_end(self, data, prefix=""):
        self.root.ids[prefix + 'logradouro'].text = data.get('logradouro', '')
        self.root.ids[prefix + 'bairro'].text = data.get('bairro', '')
        self.root.ids[prefix + 'cidade'].text = data.get('localidade', '')
        self.root.ids[prefix + 'estado'].text = data.get('uf', 'MG')
        toast("Endereço carregado!")

    def buscar_solar(self, prefix=""):
        cidade = self.root.ids[prefix + 'cidade'].text; estado = self.root.ids[prefix + 'estado'].text
        if not cidade: toast("Preencha a cidade!"); return
        def run():
            try:
                ctx = ssl.create_default_context(cafile=certifi.where())
                geolocator = Nominatim(user_agent="kivy_solar_app_v65", ssl_context=ctx)
                loc = geolocator.geocode(f"{cidade}, {estado}, Brazil")
                if loc:
                    if prefix == "":
                        self.lat = f"{loc.latitude:.6f}"; self.lon = f"{loc.longitude:.6f}"
                    else:
                        self.lat_hib = f"{loc.latitude:.6f}"; self.lon_hib = f"{loc.longitude:.6f}"
                    url = f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude={loc.longitude}&latitude={loc.latitude}&format=JSON"
                    r = requests.get(url, timeout=10, verify=certifi.where()).json()
                    mensal_data = r['properties']['parameter']['ALLSKY_SFC_SW_DWN']
                    chaves = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
                    irr = [mensal_data.get(m, 5.0) for m in chaves]
                    if prefix == "": self.irradiacao_mensal = irr
                    else: self.irradiacao_mensal_hib = irr
                    media = mensal_data.get('ANN', 5.1)
                    Clock.schedule_once(lambda dt: self.atualizar_hsp(media, prefix))
                else: Clock.schedule_once(lambda dt: toast("Cidade não encontrada no mapa"))
            except Exception as e:
                err = str(e); Clock.schedule_once(lambda dt: toast(f"Erro busca: {err[:20]}"))
        threading.Thread(target=run).start()

    def atualizar_hsp(self, valor, prefix=""):
        self.root.ids[prefix + 'hsp'].text = fmt_br(valor, 2)
        toast("Dados da NASA atualizados!")

    def calcular_sugestao(self, prefix=""):
        meta_manual = self.root.ids[prefix + 'meta_geracao'].text; consum_final = 0.0
        if meta_manual and parse_br(meta_manual) > 0:
            consum_final = parse_br(meta_manual)
            self.root.ids[prefix + 'lbl_consumo_usado'].text = f"Usando Meta Manual: {fmt_br(consum_final)} kWh"
        else:
            soma = 0
            for i in range(1, 13):
                val = self.root.ids[prefix + f"mes_{i}"].text
                if val: soma += parse_br(val)
            media = soma / 12
            if self.root.ids[prefix + 'switch_aumento'].active:
                try: media += parse_br(self.root.ids[prefix + 'valor_aumento'].text)
                except: pass
            consum_final = media
            self.root.ids[prefix + 'lbl_consumo_usado'].text = f"Usando Histórico: {fmt_br(consum_final)} kWh"
        
        if prefix == "": self.consumo_final_usado = consum_final
        else: self.consumo_final_usado_hib = consum_final
            
        try:
            hsp = parse_br(self.root.ids[prefix + 'hsp'].text)
            if hsp == 0: hsp = 5.1
            pot = consum_final / (hsp * 30 * 0.75)
            
            # 1. Sugestão de Módulos (Pega o de maior potência no DB para melhor eficiência)
            modulos = db.get_modulos()
            if modulos:
                modulos.sort(key=lambda x: x[1], reverse=True)
                mod_nome, mod_pot = modulos[0]
                
                qtd = math.ceil((pot * 1000) / mod_pot)
                if qtd < 2: qtd = 2
                pot_instalada = (qtd * mod_pot) / 1000.0
                
                self.root.ids[prefix + 'nome_modulo'].text = f"{mod_nome} ({fmt_br(mod_pot, 0)}W)"
            else:
                qtd = math.ceil(pot / 0.555)
                if qtd < 2: qtd = 2
                pot_instalada = pot
                
            self.root.ids[prefix + 'qtd_modulos'].text = str(qtd)
            self.root.ids[prefix + 'lbl_resultado_kwp'].text = f"Potência: {fmt_br(pot_instalada, 2)} kWp"
            
            # 2. Sugestão de Inversor (Filtra o ideal com regra de até 20% de Overload)
            inversores = db.get_inversores()
            if inversores:
                invs_validos = []
                for inv_nome, inv_pot, img_path in inversores:
                    is_hib = "HIBRIDO" in inv_nome.upper() or "HÍBRIDO" in inv_nome.upper()
                    if prefix == 'hib_' and not is_hib: continue
                    if prefix == '' and is_hib: continue
                    invs_validos.append((inv_nome, inv_pot, img_path))
                
                if invs_validos:
                    invs_validos.sort(key=lambda x: x[1])
                    melhor_inv = invs_validos[-1] # Por padrão pega o maior disponível
                    
                    for inv in invs_validos:
                        if inv[1] >= (pot_instalada / 1.2):
                            melhor_inv = inv
                            break
                            
                    inv_nome, inv_pot, img_path = melhor_inv
                    
                    campo_inv = prefix + 'sel_inversor' if prefix == 'hib_' else prefix + 'nome_inversor'
                    self.root.ids[campo_inv].text = f"{inv_nome} ({fmt_br(inv_pot, 1)}kW)"
                    self.root.ids[prefix + 'qtd_inversor'].text = "1"
                    
                    if prefix == 'hib_':
                        self.img_inversor_hibrido = img_path
                    else:
                        self.img_inversor_orcamento = img_path
                        
            self.atualizar_potencia_kit(prefix)
            toast("Kit Sugerido com Sucesso!")
        except Exception as e: 
            toast(f"Erro ao sugerir kit: {str(e)[:20]}")

    def buscar_tarifa_cemig(self, prefix=""):
        toast("Buscando tarifa no site da CEMIG...")
        def run():
            try:
                import re
                import urllib3
                
                # Desativa avisos de segurança SSL que causam erros em alguns computadores/celulares
                urllib3.disable_warnings()
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # A CEMIG atualiza o site com frequência. Vamos tentar as URLs conhecidas:
                urls = [
                    "https://www.cemig.com.br/atendimento/tarifas-vigentes/",
                    "https://www.cemig.com.br/valores-e-tarifas/tarifas-vigentes/",
                    "https://www.cemig.com.br/atendimento/valores-de-tarifas-e-servicos/"
                ]
                
                html = None
                for url in urls:
                    res = requests.get(url, headers=headers, timeout=15, verify=False)
                    if res.status_code == 200:
                        html = res.text.upper()
                        break
                
                if html:
                    valor_encontrado = None
                    
                    # Sem depender do BeautifulSoup (evita o erro 'No module named bs4' no Android/Windows)
                    tr_pattern = re.compile(r'<TR[^>]*>.*?</TR>', re.IGNORECASE | re.DOTALL)
                    
                    for tr_match in tr_pattern.finditer(html):
                        tr_text = tr_match.group(0)
                        
                        # Identifica a linha da tarifa B1 Residencial Normal
                        if 'B1' in tr_text and 'RESIDENCIAL' in tr_text and 'NORMAL' in tr_text:
                            # Busca o primeiro número no formato X,XXXX
                            matches = re.findall(r'(\d+,\d{4,5})', tr_text)
                            if matches:
                                v_float = float(matches[0].replace(',', '.'))
                                # O site mostra a tarifa base. O custo real leva ~35% de impostos (ICMS/PIS/COFINS).
                                valor_real = v_float * 1.35
                                valor_encontrado = f"{valor_real:.2f}".replace('.', ',')
                                break
                    
                    if valor_encontrado:
                        Clock.schedule_once(lambda dt: self.atualizar_tarifa(valor_encontrado, prefix))
                    else:
                        Clock.schedule_once(lambda dt: toast("Tarifa B1 não encontrada na página."))
                else:
                    Clock.schedule_once(lambda dt: toast(f"Erro ao acessar CEMIG: HTTP {res.status_code}"))
            except Exception as e:
                err = str(e)
                Clock.schedule_once(lambda dt: toast(f"Erro busca: {err[:25]}"))
        
        threading.Thread(target=run).start()

    def atualizar_tarifa(self, valor, prefix=""):
        self.root.ids[prefix + 'valor_kwh'].text = valor
        if prefix == "": db.set_config('valor_kwh', valor)
        toast(f"Tarifa Atualizada: R$ {valor} (Com Impostos Estimados)")

    def gerar_grafico(self, pot, prefix=""):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
        
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        vals = []
        irr = self.irradiacao_mensal if prefix == "" else getattr(self, 'irradiacao_mensal_hib', [5.1]*12)
        for i in range(12): vals.append(pot * irr[i] * 30 * 0.75)
        
        fig = Figure(figsize=(8, 3))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        bars = ax.bar(meses, vals, color='#009933', width=0.5)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 10, f'{int(height)}', ha='center', va='bottom', rotation=90, fontsize=8, color='black')
        ax.grid(axis='y', linestyle='-', alpha=0.3); ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        if vals: ax.set_ylim(0, max(vals) * 1.4)
        
        fig.tight_layout()
        nome_img = f"temp_graf_{prefix}.png" if prefix else "temp_graf.png"
        canvas.print_png(nome_img)

    def preparar_pdf(self):
        nome = self.root.ids.nome.text
        if not nome: toast("Preencha o Nome"); return
        try: kwh_price = parse_br(self.root.ids.valor_kwh.text) or 1.16
        except: kwh_price = 1.16
        
        num_prop_atual = self.root.ids.config_num_prop.text
        if not num_prop_atual or not num_prop_atual.isdigit(): num_prop_atual = "100"

        dados = {
            'nome': nome, 'cpf': self.root.ids.cpf.text, 'logradouro': self.root.ids.logradouro.text, 'numero': self.root.ids.numero.text,
            'complemento': self.root.ids.complemento.text, 'bairro': self.root.ids.bairro.text, 'cidade': self.root.ids.cidade.text,
            'estado': self.root.ids.estado.text, 'classificacao': self.root.ids.classificacao.text, 
            'hsp': parse_br(self.root.ids.hsp.text or "5.1"),
            'consumo_val': self.consumo_final_usado, 
            'custo_equip': parse_br(self.root.ids.custo_equip.text or "0"), 
            'mao_obra': parse_br(self.root.ids.mao_obra.text or "0"),
            'qtd_modulos': self.root.ids.qtd_modulos.text, 'nome_modulo': self.root.ids.nome_modulo.text, 'qtd_inversor': self.root.ids.qtd_inversor.text,
            'nome_inversor': self.root.ids.nome_inversor.text, 'qtd_estrutura': self.root.ids.qtd_estrutura.text, 'nome_estrutura': self.root.ids.nome_estrutura.text,
            'qtd_cabo': self.root.ids.qtd_cabo.text, 'qtd_conectores': self.root.ids.qtd_conectores.text, 'lat': self.lat, 'lon': self.lon,
            'valor_kwh': kwh_price, 'img_inversor': self.img_inversor_orcamento,
            'num_proposta': num_prop_atual
        }
        toast("Gerando PDF... Aguarde"); threading.Thread(target=self.gerar_pdf, args=(dados,)).start()

    def gerar_pdf(self, d):
        try:
            pdf = PDF(); pdf.set_auto_page_break(auto=True, margin=15)
            hoje = datetime.date.today()
            # Mapeamento com acentos corrigidos
            meses_txt = {
                1: limpar_texto('JANEIRO'), 2: limpar_texto('FEVEREIRO'), 3: limpar_texto('MARÇO'), 
                4: limpar_texto('ABRIL'), 5: limpar_texto('MAIO'), 6: limpar_texto('JUNHO'), 
                7: limpar_texto('JULHO'), 8: limpar_texto('AGOSTO'), 9: limpar_texto('SETEMBRO'), 
                10: limpar_texto('OUTUBRO'), 11: limpar_texto('NOVEMBRO'), 12: limpar_texto('DEZEMBRO')
            }
            
            num_prop_str = d.get('num_proposta', '100')
            num_prop = f"{num_prop_str}/{hoje.year}-G rev00"
            id_cli = f"{num_prop_str} - {hoje.year}"
            
            qtd = int(d['qtd_modulos'] or "0")
            pot_modulo_w = 555.0
            for n, p in sorted(db.get_modulos(), key=lambda x: len(x[0]), reverse=True):
                if d['nome_modulo'] and d['nome_modulo'].startswith(n):
                    pot_modulo_w = float(p)
                    break
            pot = (qtd * pot_modulo_w) / 1000.0
            area = qtd * 2.2; peso = area * 20; total = d['custo_equip'] + d['mao_obra']
            
            # PAG 1
            pdf.add_page(); pdf.set_y(35); pdf.set_font("Arial", "", 20)
            data_extenso = f"{hoje.day} DE {meses_txt[hoje.month]} DE {hoje.year}"
            pdf.cell(0, 10, limpar_texto(data_extenso), ln=True, align='R')
            
            pdf.set_y(100); pdf.set_font("Arial", "B", 28); pdf.cell(0, 12, limpar_texto("PROPOSTA TÉCNICA / COMERCIAL"), ln=True, align='C')
            pdf.cell(0, 12, limpar_texto("INSTALAÇÃO DE ENERGIA"), ln=True, align='C')
            cy = pdf.get_y(); pdf.cell(0, 12, limpar_texto("FOTOVOLTAICA"), ln=False, align='C')
            pdf.set_font("Arial", "B", 10); pdf.set_xy(90, cy+2); pdf.cell(100, 50, limpar_texto(f"Nº. da proposta {num_prop}"), align='R')
            pdf.set_y(-60); pdf.set_x(100); pdf.set_font("Arial", "", 11)
            pdf.multi_cell(90, 6, limpar_texto("Proposta técnica e comercial para elaboração de projeto, fornecimento de equipamento e instalação de usina fotovoltaica para geração de energia elétrica."), align='R')

            # PAG 2
            pdf.add_page(); pdf.ln(35); cw = 190
            pdf.table_cell(limpar_texto("Nome do responsável técnico:"), "Gustavo de Oliveira Silva", cw, ln=1, align='C', round_corners=True)
            pdf.table_cell(limpar_texto("Título Profissional:"), "ENGENHEIRO ELETRICISTA", 95, align='C', round_corners=True)
            pdf.table_cell("Registro Crea:", "255698", 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("CNPJ:", "02.534.614/0001-89", cw, ln=1, align='C', round_corners=True)
            pdf.set_font("Arial", 'B', 8); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 12, 2)
            pdf.cell(190, 6, limpar_texto("Serviços a prestar:"), 0, 1, 'C'); pdf.set_font("Arial", '', 8)
            pdf.multi_cell(190, 5, limpar_texto("Orçamentos de instalação dos equipamentos de geração de energia fotovoltaica."), 0, 'C')
            pdf.set_y(pdf.get_y() + 2)
            pdf.set_font("Arial", 'B', 8); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 18, 2)
            pdf.cell(190, 6, limpar_texto("Não incluso -"), 0, 1, 'C'); pdf.set_font("Arial", '', 8)
            pdf.multi_cell(190, 4, limpar_texto("(caso necessário): Troca de padrão, adequação de rede, obras de construção civil, troca de transformadores, licença ambiental, serviços de nivelamento de terreno e aluguel de andaimes e máquinas."), 0, 'C')
            pdf.set_y(pdf.get_y() + 5)
            pdf.set_font("Arial", 'B', 12); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 10, 2)
            pdf.cell(190, 10, limpar_texto("Telefone: (31)996994716 – (33)99140-5260"), 0, 1, 'C')
            pdf.set_font("Arial", 'B', 9); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 8, 2)
            pdf.cell(190, 8, limpar_texto("Endereço: Av. Prefeito José Surdo nº 1196, Centro, Mateus Leme - MG"), 0, 1, 'C')
            pdf.ln(10); pdf.set_font("Arial", '', 24); pdf.cell(190, 10, "Contratante:", align='C', ln=1); pdf.ln(5)
            
            # Limpeza dos dados do usuário
            pdf.table_cell("Nome do contratante:", d['nome'], 190, ln=1, align='C', round_corners=True)
            pdf.table_cell("CPF:", d['cpf'], 95, align='C', round_corners=True); pdf.table_cell("ID Cliente:", id_cli, 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("Logradouro:", d['logradouro'], 190, ln=1, align='C', round_corners=True)
            pdf.table_cell(limpar_texto("Número:"), d['numero'], 95, align='C', round_corners=True); pdf.table_cell("Complemento:", d['complemento'], 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("Bairro:", d['bairro'], 95, align='C', round_corners=True); pdf.table_cell("Cidade:", d['cidade'], 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("Estado:", d['estado'], 190, ln=1, align='C', round_corners=True)
            pdf.table_cell("Latitude:", d['lat'], 95, align='C', round_corners=True); pdf.table_cell("Longitude:", d['lon'], 95, ln=1, align='C', round_corners=True)

            # PAG 3
            pdf.add_page(); pdf.ln(35); pdf.set_font("Arial", 'B', 24); pdf.cell(0, 5, limpar_texto("ORÇAMENTO"), ln=True, align='L'); pdf.ln(10)
            pdf.set_font("Arial", '', 11)
            txt = f"Este documento apresenta o valor da construção de uma usina fotovoltaica com relação a geração distribuída. A compensação de créditos é feita via concessionária de energia de sua região (CEMIG).\n\nSão levantados todos os custos que serão investidos no sistema fotovoltaico, como, a instalação, estrutura para acomodamento das placas, projeto para execução e aprovação na concessionária de energia.\n\nO orçamento foi feito na base de consumo de {fmt_br(d['consumo_val'])} KWh/mês em sua conta, com uma taxa de irradiação de {fmt_br(d['hsp'])} KWh/m².dia proveniente da cidade de {d['cidade']}."
            pdf.multi_cell(0, 6, limpar_texto(txt), align='J'); pdf.ln(15)
            pdf.set_font("Arial", 'B', 12); pdf.cell(0, 5, limpar_texto("Tabela 1 – Informações"), ln=True, align='C')
            tx = (210-160)/2; ty = pdf.get_y(); pdf.set_fill_color(240, 240, 240); pdf.rounded_rect(tx, ty, 160, 48, 3, style='F')
            
            rows = [("Consumo Médio mensal:", f"{fmt_br(d['consumo_val'])} KWh"), ("Potência Instalada:", f"{fmt_br(pot)} KWp"), ("Peso:", f"{fmt_br(peso, 0)} Kg"), ("Área necessária:", f"{fmt_br(area, 1)} M²")]
            pdf.set_y(ty); rh = 12; clw = 90; cvw = 70
            for l, v in rows:
                pdf.set_x(tx); pdf.set_fill_color(225, 225, 225); pdf.set_font("Arial", 'B', 10); pdf.cell(clw, rh, limpar_texto(l), 0, 0, 'R', fill=True)
                pdf.set_fill_color(245, 245, 245); pdf.set_font("Arial", '', 10); pdf.cell(cvw, rh, limpar_texto(f"   {v}"), 0, 1, 'L', fill=True)
            pdf.rounded_rect(tx, ty, 160, 48, 3, style='D'); pdf.ln(15)
            
            self.gerar_grafico(pot); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("Tabela 2 – Quantidade de KWh por mês a ser gerado."), ln=True, align='C')
            pdf.image("temp_graf.png", x=tx, w=160); os.remove("temp_graf.png")

            # PAG 4
            pdf.add_page(); pdf.ln(39); pdf.set_font("Arial", 'B', 18); pdf.cell(0, 10, limpar_texto("      1 - COMPOSIÇÃO DO KIT;"), ln=True); pdf.ln(15)
            ki = []
            if d['qtd_conectores'] and d['qtd_conectores'] != "0": ki.append(f"{d['qtd_conectores']}    PARES DE CONECTORES MC4")
            if d['qtd_cabo'] and d['qtd_cabo'] != "0":
                ki.append(f"{d['qtd_cabo']}     CABO SOLAR FOTOVOLTAICO FLEXIVEL 6MM 1,8KV CC RL 25 VERMELHO")
                ki.append(f"{d['qtd_cabo']}     CABO SOLAR FOTOVOLTAICO FLEXIVEL 6MM 1,8KV CC RL 25 PRETO")
            if d['qtd_estrutura'] and d['qtd_estrutura'] != "0": ki.append(f"{d['qtd_estrutura']} {d['nome_estrutura'].upper()}")
            if d['qtd_modulos'] and d['qtd_modulos'] != "0": ki.append(f"{d['qtd_modulos']} {d['nome_modulo'].upper()}")
            if d['qtd_inversor'] and d['qtd_inversor'] != "0": ki.append(f"{d['qtd_inversor']} {d['nome_inversor'].upper()}")
            pdf.set_font("Arial", '', 10)
            for it in ki:
                if pdf.get_y() > 270: pdf.add_page()
                cx, cy = pdf.get_x() + 15, pdf.get_y() + 3
                pdf.line(cx, cy-1.5, cx+1.5, cy); pdf.line(cx+2.5, cy, cx, cy+1.5); pdf.line(cx, cy+1.5, cx-1.5, cy); pdf.line(cx-2.5, cy, cx, cy-1.5)
                pdf.set_x(30); pdf.multi_cell(0, 6, limpar_texto(it), align='L'); pdf.ln(5)

            # PAG 5
            pdf.add_page(); pdf.ln(30); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("Imagem 1 – Imagens do Inversor"), ln=True, align='C')
            if d['img_inversor'] and os.path.exists(d['img_inversor']): x_img = (210-80)/2; pdf.image(d['img_inversor'], x=x_img, w=105)
            pdf.ln(12); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, limpar_texto("2 – VALORES;"), ln=True); pdf.cell(0, 8, limpar_texto(f"2.1 KIT {fmt_br(pot)} KW"), ln=True)
            def drow(txt):
                if pdf.get_y() > 270: pdf.add_page()
                pdf.set_font("Arial", '', 10); cx, cy = pdf.get_x() + 5, pdf.get_y() + 5
                pdf.line(cx, cy-1.5, cx+1.5, cy); pdf.line(cx+1.5, cy, cx, cy+1.5); pdf.line(cx, cy+1.5, cx-1.5, cy); pdf.line(cx-1.5, cy, cx, cy-1.5)
                pdf.set_x(20); w_label = pdf.get_string_width(txt); pdf.cell(w_label + 2, 10, limpar_texto(txt), 0, 0)
                w_dots = 170 - w_label - 5; 
                if w_dots > 0: pdf.cell(w_dots, 10, "." * int(w_dots / pdf.get_string_width(".")), 0, 0, 'L')
                pdf.ln(10)
            drow(f"01 Kit Energia fotovoltaica para {fmt_br(pot)}Kwp"); drow("01 Projeto Sistema Fotovoltaico (C\\ART)"); drow("01 Materiais Ac do Sistema"); drow("01 Instalação do Sistema")
            
            pdf.ln(5); pdf.set_font("Arial", 'B', 12); lbl_tot = "VALOR TOTAL R$: "; w_lbl = pdf.get_string_width(lbl_tot); val_tot = fmt_br(total, 2); w_val = pdf.get_string_width(val_tot)
            x_start = 210 - 20 - w_lbl - w_val
            pdf.set_x(x_start); pdf.cell(w_lbl, 10, lbl_tot, 0, 0, 'L'); pdf.set_font("Arial", '', 12); pdf.cell(w_val, 10, val_tot, 0, 1, 'L')
            pdf.ln(5); pdf.set_font("Arial", 'B', 9); pdf.write(5, "OBS. ATENÇÃO "); pdf.set_font("Arial", '', 9); pdf.write(5, limpar_texto("Os equipamentos sofrem variação no preço conforme o valor do dólar em relação a nossa moeda nacional."))

            # PAG 6
            pdf.add_page(); pdf.ln(45); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, limpar_texto("3 - RETORNO DO INVESTIMENTO;"), ln=True); pdf.ln(5)
            kwh_txt = fmt_br(d['valor_kwh'], 2)
            pdf.set_font("Arial", '', 10)
            obs_txt = f"Obs: Estimativa baseada no consumo de {fmt_br(d['consumo_val'])} kWh/mês (Tarifa atual: R$ {kwh_txt}). O cálculo do retorno leva em consideração um reajuste tarifário (inflação energética) estimado em 8% ao ano. A economia gerada é reajustada anualmente por essa taxa e somada de forma cumulativa."
            pdf.multi_cell(0, 5, limpar_texto(obs_txt)); pdf.ln(10)
            pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, limpar_texto("Tabela 3 – Previsão de retorno do investimento."), ln=True, align='C'); pdf.ln(2)
            caw = 60; cvw = 80; xs = (210 - (caw + cvw)) / 2; pdf.set_x(xs); pdf.set_font("Arial", 'B', 10); pdf.cell(caw, 8, "Ano", 0, 0, 'C'); pdf.cell(cvw, 8, "Valor do retorno (R$)", 0, 1, 'C')
            ea = float(d['consumo_val']) * d['valor_kwh'] * 12
            ac = 0
            inflacao_energia = 0.08  # Estimativa de 8% ao ano
            pdf.set_font("Arial", '', 10)
            for i in range(1, 11):
                if pdf.get_y() > 270: pdf.add_page()
                ac += ea
                ea *= (1 + inflacao_energia)
                if i % 2 != 0: pdf.set_fill_color(225, 235, 255); fill = True
                else: pdf.set_fill_color(255, 255, 255); fill = True
                pdf.set_font("Arial", '', 10); pdf.set_x(xs); pdf.cell(caw, 8, str(i), 0, 0, 'C', fill=True); vstr = f"R$ {fmt_br(ac, 2)}"; pdf.cell(cvw, 8, vstr, 0, 1, 'C', fill=True)
            pdf.ln(15); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, limpar_texto("6 – GARANTIAS;"), ln=True); pdf.ln(5); pdf.set_font("Arial", '', 10)
            ws = ["A garantia do inversor e baterias é conforme especificação da fábrica.", "Garantia de 12 anos das placas pela fábrica contra defeitos de fabricação.", "Garantia de 1 ano de serviço de instalação do sistema.", "Garantia de 10 anos para estruturas de fixação."]
            for w in ws:
                if pdf.get_y() > 270: pdf.add_page()
                cy = pdf.get_y(); pdf.set_fill_color(0, 0, 0); pdf.rect(20, cy + 1.5, 1.5, 1.5, 'F'); pdf.set_x(25); pdf.multi_cell(0, 5, limpar_texto(w)); pdf.ln(3)

            # PAG 8 - Pagamento e Cronograma
            pdf.add_page(); pdf.ln(45); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("7 - CONDIÇÕES DE PAGAMENTO;"), ln=True)
            pdf.set_font("Arial", '', 11); pdf.multi_cell(0, 6, limpar_texto("Trabalhamos com financiamento de até 100% do valor, temos parceria com alguns bancos. Solicite sua simulação.")); pdf.ln(10)
            pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("Observações:"), ln=True); pdf.set_font("Arial", '', 11)
            oi = ["1. Esta proposta pode ser revisada caso necessário.", "2. A garantia começa a contar após a instalação do equipamento.", "3. Fica a cargo do instalador/projetista, todos as responsabilidades envolvendo a instalação do sistema."]
            for it in oi: pdf.multi_cell(0, 6, limpar_texto(it)); pdf.ln(2)

            pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("8 – CRONOGRAMA DE EXECUÇÃO;"), ln=True); pdf.ln(5)
            x_start = 20; pdf.set_fill_color(220, 230, 240); pdf.set_x(x_start); pdf.cell(90, 10, "ETAPA", 1, 0, 'C', fill=True); pdf.cell(80, 10, limpar_texto("PRAZO"), 1, 1, 'C', fill=True)
            ic = [("PROJETO", "5 DIAS"), ("CONSULTA CEMIG", "15 DIAS"), ("ENTREGA E INSTALAÇÃO", "25 DIAS"), ("TROCA MEDIDOR", "PRAZO CEMIG")]
            pdf.set_font("Arial", '', 10)
            for e_nome, p in ic:
                if pdf.get_y() > 270: pdf.add_page()
                pdf.set_x(x_start); pdf.cell(90, 10, limpar_texto(e_nome), 1, 0, 'L'); pdf.cell(80, 10, limpar_texto(p), 1, 1, 'L')
            
            if pdf.get_y() > 250: pdf.add_page()
            pdf.ln(12); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("9 – VALIDAÇÃO DA PROPOSTA"), ln=True); pdf.ln(20)
            line_width = 140; x_line = (210 - line_width) / 2; pdf.line(x_line, pdf.get_y(), x_line + line_width, pdf.get_y()); pdf.ln(2)
            
            x_sig = (210 - 80) / 2
            def sign_line(lbl, val):
                pdf.set_font("Arial", 'B', 10); pdf.cell(15, 5, lbl, 0, 0, 'R')
                pdf.set_font("Arial", '', 10); pdf.cell(0, 5, val, 0, 1, 'L')
            pdf.set_x(x_sig); sign_line("Nome:", "Gustavo de Oliveira Silva")
            pdf.set_x(x_sig); sign_line("Cargo:", limpar_texto("Responsável técnico"))
            pdf.set_x(x_sig); sign_line("CPF:", "113.185.936-70")

            nome_arq = f"{num_prop_str}-{d['nome']}-{fmt_br(pot)}kWp.pdf"
            folder_path = db.get_config('pdf_path')
            
            if kivy_platform == "android":
                if folder_path and os.path.exists(folder_path): out_path = os.path.join(folder_path, nome_arq)
                else:
                    from android.storage import primary_external_storage_path
                    dir_path = os.path.join(primary_external_storage_path(), 'Download')
                    out_path = os.path.join(dir_path, nome_arq)
                pdf.output(out_path)
                Clock.schedule_once(lambda dt: toast(f"Salvo em: {out_path}"))
            else:
                if folder_path and os.path.exists(folder_path): nome_arq = os.path.join(folder_path, nome_arq)
                pdf.output(nome_arq)
                try: os.startfile(nome_arq)
                except: pass
                Clock.schedule_once(lambda dt: toast("PDF Gerado com Sucesso!"))

            try:
                prox_num = int(num_prop_str) + 1
                db.set_config('num_proposta', str(prox_num))
                Clock.schedule_once(lambda dt: setattr(self.root.ids.config_num_prop, 'text', str(prox_num)))
            except: pass

        except Exception as e:
            err_msg = str(e)
            Clock.schedule_once(lambda dt: toast(f"Erro: {err_msg}"))

    def limpar_hibrido(self):
        ids = self.root.ids
        campos = ['hib_nome', 'hib_cpf', 'hib_cep', 'hib_logradouro', 'hib_numero', 
                  'hib_complemento', 'hib_bairro', 'hib_cidade', 'hib_estado', 
                  'hib_consumo_critico', 'hib_tensao_banco', 'hib_capacidade_bateria', 
                  'hib_custo_equip', 'hib_mao_obra', 'hib_custo_baterias', 
                  'hib_sel_bateria', 'hib_sel_inversor', 'hib_nome_modulo', 'hib_nome_estrutura',
                  'hib_qtd_modulos', 'hib_qtd_inversor', 'hib_qtd_estrutura', 'hib_qtd_cabo',
                  'hib_qtd_conectores', 'hib_meta_geracao', 'hib_valor_aumento']
        
        for i in range(1, 13):
            campos.append(f'hib_mes_{i}')
            
        for c in campos:
            if c in ids: ids[c].text = ""
            
        ids.hib_classificacao.text = "Residencial"
        ids.hib_dod.text = "80"
        ids.hib_hsp.text = "5,1"
        ids.hib_switch_aumento.active = False
        
        self.img_inversor_hibrido = None
        self.consumo_final_usado_hib = 0.0
        # Oculta o card de resultados novamente
        ids.hib_resultado_card.opacity = 0
        ids.hib_resultado_card.disabled = True

    def calcular_orcamento_hibrido(self):
        ids = self.root.ids
        try:
            # Roda o cálculo de sugestão solar automaticamente
            self.calcular_sugestao('hib_')
            qtd_modulos = ids.hib_qtd_modulos.text
            pot_necessaria = ids.hib_lbl_resultado_kwp.text.replace("Potência Necessária: ", "").replace("Potência: ", "")
            
            # Coleta e higienização dos valores da tela
            tensao = parse_br(ids.hib_tensao_banco.text)
            cap_ah = parse_br(ids.hib_capacidade_bateria.text)
            dod = parse_br(ids.hib_dod.text)
            cons_critico = parse_br(ids.hib_consumo_critico.text)
            
            custo_inv = parse_br(ids.hib_custo_equip.text)
            custo_bat = parse_br(ids.hib_custo_baterias.text)
            custo_inst = parse_br(ids.hib_mao_obra.text)

            # Lógica Matemática Aplicada
            cap_total_kwh = (tensao * cap_ah) / 1000.0
            energia_util = cap_total_kwh * (dod / 100.0) * 0.95
            
            if cons_critico > 0:
                autonomia_dias = energia_util / cons_critico
                autonomia_horas = autonomia_dias * 24.0
            else:
                autonomia_dias = 0.0
                autonomia_horas = 0.0
                
            custo_total = custo_inv + custo_bat + custo_inst
            preco_final = custo_total

            # Alimentação da Interface Visual do Card
            ids.hib_res_capacidade.text = f"Capacidade Total: {fmt_br(cap_total_kwh, 2)} kWh"
            ids.hib_res_util.text = f"Energia Útil: {fmt_br(energia_util, 2)} kWh"
            ids.hib_res_autonomia.text = f"Autonomia: {fmt_br(autonomia_dias, 1)} dias ({fmt_br(autonomia_horas, 0)} horas)"
            ids.hib_res_kit.text = f"Kit Solar: {pot_necessaria} ({qtd_modulos} Painéis e 1 Inversor)"
            ids.hib_res_preco.text = f"Preço Final de Venda: R$ {fmt_br(preco_final, 2)}"
            
            # Torna o Card visível para o usuário
            ids.hib_resultado_card.opacity = 1
            ids.hib_resultado_card.disabled = False
            
            toast("Dimensionamento Calculado!")
        except Exception as e:
            toast("Erro no cálculo: Verifique os valores inseridos.")

    def preparar_pdf_hibrido(self):
        ids = self.root.ids
        nome = ids.hib_nome.text
        if not nome: 
            toast("Preencha o Nome do Cliente!")
            return
            
        try:
            try: kwh_price = parse_br(ids.hib_valor_kwh.text) or 1.16
            except: kwh_price = 1.16

            dados = {
                'nome': nome, 'cpf': ids.hib_cpf.text, 'logradouro': ids.hib_logradouro.text, 
                'numero': ids.hib_numero.text, 'complemento': ids.hib_complemento.text, 
                'bairro': ids.hib_bairro.text, 'cidade': ids.hib_cidade.text,
                'estado': ids.hib_estado.text, 'classificacao': ids.hib_classificacao.text, 
                'hsp': parse_br(ids.hib_hsp.text or "5.1"),
                'consumo_val': getattr(self, 'consumo_final_usado_hib', 0), 
                
                'consumo_critico': parse_br(ids.hib_consumo_critico.text),
                'tensao_banco': parse_br(ids.hib_tensao_banco.text),
                'capacidade_bateria': parse_br(ids.hib_capacidade_bateria.text),
                'dod': parse_br(ids.hib_dod.text),
                
                'custo_equip': parse_br(ids.hib_custo_equip.text),
                'custo_bat': parse_br(ids.hib_custo_baterias.text),
                'mao_obra': parse_br(ids.hib_mao_obra.text),
                
                'qtd_modulos': ids.hib_qtd_modulos.text, 'nome_modulo': ids.hib_nome_modulo.text, 
                'qtd_inversor': ids.hib_qtd_inversor.text, 'inversor_nome': ids.hib_sel_inversor.text, 
                'qtd_estrutura': ids.hib_qtd_estrutura.text, 'nome_estrutura': ids.hib_nome_estrutura.text,
                'qtd_cabo': ids.hib_qtd_cabo.text, 'qtd_conectores': ids.hib_qtd_conectores.text, 
                'lat': getattr(self, 'lat_hib', ""), 'lon': getattr(self, 'lon_hib', ""),
                
                'valor_kwh': kwh_price, 
                'bateria_nome': ids.hib_sel_bateria.text or "Banco de Baterias",
                'img_inversor': getattr(self, 'img_inversor_hibrido', None)
            }
            
            # Recalcula para garantir os valores atuais
            cap_total_kwh = (dados['tensao_banco'] * dados['capacidade_bateria']) / 1000.0
            energia_util = cap_total_kwh * (dados['dod'] / 100.0) * 0.95
            
            if dados['consumo_critico'] > 0:
                autonomia_dias = energia_util / dados['consumo_critico']
                autonomia_horas = autonomia_dias * 24.0
            else:
                autonomia_dias = 0.0
                autonomia_horas = 0.0
                
            custo_total = dados['custo_equip'] + dados['custo_bat'] + dados['mao_obra']
            preco_final = custo_total
            
            dados['cap_total_kwh'] = cap_total_kwh
            dados['energia_util'] = energia_util
            dados['autonomia_horas'] = autonomia_horas
            dados['preco_final'] = preco_final
            
            num_prop_atual = self.root.ids.config_num_prop.text
            if not num_prop_atual or not num_prop_atual.isdigit(): num_prop_atual = "100"
            dados['num_proposta'] = num_prop_atual
            
            toast("Gerando PDF Híbrido... Aguarde")
            threading.Thread(target=self.gerar_pdf_hibrido, args=(dados,)).start()
        except Exception as e:
            toast(f"Erro ao preparar PDF: {str(e)[:30]}")

    def gerar_pdf_hibrido(self, d):
        try:
            pdf = PDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            hoje = datetime.date.today()
            meses_txt = {1: limpar_texto('JANEIRO'), 2: limpar_texto('FEVEREIRO'), 3: limpar_texto('MARÇO'), 4: limpar_texto('ABRIL'), 5: limpar_texto('MAIO'), 6: limpar_texto('JUNHO'), 7: limpar_texto('JULHO'), 8: limpar_texto('AGOSTO'), 9: limpar_texto('SETEMBRO'), 10: limpar_texto('OUTUBRO'), 11: limpar_texto('NOVEMBRO'), 12: limpar_texto('DEZEMBRO')}
            
            num_prop_str = d.get('num_proposta', '100')
            num_prop = f"{num_prop_str}/{hoje.year}-H rev00"
            id_cli = f"{num_prop_str} - {hoje.year}"
            
            qtd = int(d['qtd_modulos'] or "0")
            pot_modulo_w = 555.0
            for n, p in sorted(db.get_modulos(), key=lambda x: len(x[0]), reverse=True):
                if d['nome_modulo'] and d['nome_modulo'].startswith(n):
                    pot_modulo_w = float(p)
                    break
            pot = (qtd * pot_modulo_w) / 1000.0
            area = qtd * 2.2; peso = area * 20; 
            total = d['custo_equip'] + d['mao_obra'] + d['custo_bat']
            
            # PAG 1 - Capa
            pdf.add_page(); pdf.set_y(35); pdf.set_font("Arial", "", 20)
            data_extenso = f"{hoje.day} DE {meses_txt[hoje.month]} DE {hoje.year}"
            pdf.cell(0, 10, limpar_texto(data_extenso), ln=True, align='R')
            
            pdf.set_y(100); pdf.set_font("Arial", "B", 28)
            pdf.cell(0, 12, limpar_texto("PROPOSTA TÉCNICA / COMERCIAL"), ln=True, align='C')
            pdf.cell(0, 12, limpar_texto("SISTEMA FOTOVOLTAICO HÍBRIDO"), ln=True, align='C')
            cy = pdf.get_y(); pdf.cell(0, 12, limpar_texto("(COM BACKUP DE BATERIAS)"), ln=False, align='C')
            pdf.set_font("Arial", "B", 10); pdf.set_xy(90, cy+2); pdf.cell(100, 50, limpar_texto(f"Nº. da proposta {num_prop}"), align='R')
            pdf.set_y(-60); pdf.set_x(100); pdf.set_font("Arial", "", 11)
            pdf.multi_cell(90, 6, limpar_texto("Proposta técnica e comercial para dimensionamento e fornecimento de sistema de energia solar híbrido com banco de baterias para segurança e autonomia energética."), align='R')

            # PAG 2 - Responsável + Cliente
            pdf.add_page(); pdf.ln(35)
            cw = 190
            pdf.table_cell(limpar_texto("Nome do responsável técnico:"), "Gustavo de Oliveira Silva", cw, ln=1, align='C', round_corners=True)
            pdf.table_cell(limpar_texto("Título Profissional:"), "ENGENHEIRO ELETRICISTA", 95, align='C', round_corners=True)
            pdf.table_cell("Registro Crea:", "255698", 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("CNPJ:", "02.534.614/0001-89", cw, ln=1, align='C', round_corners=True)
            pdf.set_font("Arial", 'B', 8); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 12, 2)
            pdf.cell(190, 6, limpar_texto("Serviços a prestar:"), 0, 1, 'C'); pdf.set_font("Arial", '', 8)
            pdf.multi_cell(190, 5, limpar_texto("Orçamentos de instalação dos equipamentos de geração de energia fotovoltaica."), 0, 'C')
            pdf.set_y(pdf.get_y() + 2)
            pdf.set_font("Arial", 'B', 8); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 18, 2)
            pdf.cell(190, 6, limpar_texto("Não incluso -"), 0, 1, 'C'); pdf.set_font("Arial", '', 8)
            pdf.multi_cell(190, 4, limpar_texto("(caso necessário): Troca de padrão, adequação de rede, obras de construção civil, troca de transformadores, licença ambiental, serviços de nivelamento de terreno e aluguel de andaimes e máquinas."), 0, 'C')
            pdf.set_y(pdf.get_y() + 5)
            pdf.set_font("Arial", 'B', 12); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 10, 2)
            pdf.cell(190, 10, limpar_texto("Telefone: (31)996994716 – (33)99140-5260"), 0, 1, 'C')
            pdf.set_font("Arial", 'B', 9); pdf.rounded_rect(pdf.get_x(), pdf.get_y(), 190, 8, 2)
            pdf.cell(190, 8, limpar_texto("Endereço: Av. Prefeito José Surdo nº 1196, Centro, Mateus Leme - MG"), 0, 1, 'C')
            
            pdf.ln(10); pdf.set_font("Arial", '', 24); pdf.cell(190, 10, "Contratante:", align='C', ln=1); pdf.ln(5)
            pdf.table_cell("Nome do contratante:", d['nome'], 190, ln=1, align='C', round_corners=True)
            pdf.table_cell("CPF:", d['cpf'], 95, align='C', round_corners=True); pdf.table_cell("ID Cliente:", id_cli, 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("Logradouro:", d['logradouro'], 190, ln=1, align='C', round_corners=True)
            pdf.table_cell(limpar_texto("Número:"), d['numero'], 95, align='C', round_corners=True); pdf.table_cell("Complemento:", d['complemento'], 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("Bairro:", d['bairro'], 95, align='C', round_corners=True); pdf.table_cell("Cidade:", d['cidade'], 95, ln=1, align='C', round_corners=True)
            pdf.table_cell("Estado:", d['estado'], 190, ln=1, align='C', round_corners=True)
            pdf.table_cell("Latitude:", d['lat'], 95, align='C', round_corners=True); pdf.table_cell("Longitude:", d['lon'], 95, ln=1, align='C', round_corners=True)

            # PAG 3 - Geração Solar
            pdf.add_page(); pdf.ln(35); pdf.set_font("Arial", 'B', 24); pdf.cell(0, 5, limpar_texto("1 - GERAÇÃO FOTOVOLTAICA"), ln=True, align='L'); pdf.ln(10)
            pdf.set_font("Arial", '', 11)
            txt = f"Este documento apresenta o valor da construção de uma usina fotovoltaica híbrida. A compensação de créditos é feita via concessionária de energia de sua região, e o excesso de energia / demanda crítica é armazenada no banco de baterias.\n\nO orçamento foi feito na base de consumo de {fmt_br(d['consumo_val'])} KWh/mês em sua conta, com uma taxa de irradiação de {fmt_br(d['hsp'])} KWh/m².dia proveniente da cidade de {d['cidade']}."
            pdf.multi_cell(0, 6, limpar_texto(txt), align='J'); pdf.ln(10)
            pdf.set_font("Arial", 'B', 12); pdf.cell(0, 5, limpar_texto("Tabela 1 – Informações do Gerador"), ln=True, align='C')
            tx = (210-160)/2; ty = pdf.get_y(); pdf.set_fill_color(240, 240, 240); pdf.rounded_rect(tx, ty, 160, 48, 3, style='F')
            
            rows = [("Consumo Médio mensal:", f"{fmt_br(d['consumo_val'])} KWh"), ("Potência Instalada:", f"{fmt_br(pot)} KWp"), ("Peso:", f"{fmt_br(peso, 0)} Kg"), ("Área necessária:", f"{fmt_br(area, 1)} M²")]
            pdf.set_y(ty); rh = 12; clw = 90; cvw = 70
            for l, v in rows:
                pdf.set_x(tx); pdf.set_fill_color(225, 225, 225); pdf.set_font("Arial", 'B', 10); pdf.cell(clw, rh, limpar_texto(l), 0, 0, 'R', fill=True)
                pdf.set_fill_color(245, 245, 245); pdf.set_font("Arial", '', 10); pdf.cell(cvw, rh, limpar_texto(f"   {v}"), 0, 1, 'L', fill=True)
            pdf.rounded_rect(tx, ty, 160, 48, 3, style='D'); pdf.ln(10)
            
            self.gerar_grafico(pot, 'hib_'); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("Tabela 2 – Quantidade de KWh por mês a ser gerado."), ln=True, align='C')
            pdf.image("temp_graf_hib_.png", x=tx, w=160); os.remove("temp_graf_hib_.png")

            # PAG 4 - Dimensionamento do Backup
            pdf.add_page(); pdf.ln(35); pdf.set_font("Arial", 'B', 18); pdf.cell(0, 10, limpar_texto("      2 - DIMENSIONAMENTO DO BACKUP (BATERIAS)"), ln=True); pdf.ln(10)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 6, limpar_texto(f"O sistema foi dimensionado para suportar um consumo crítico diário de {fmt_br(d['consumo_critico'])} kWh. Isso garante que os equipamentos essenciais continuem funcionando mesmo durante quedas de energia da concessionária."), align='J')
            
            pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 5, limpar_texto("Tabela 1 – Parâmetros do Armazenamento"), ln=True, align='C')
            tx = (210-160)/2; ty = pdf.get_y(); pdf.set_fill_color(240, 240, 240); pdf.rounded_rect(tx, ty, 160, 60, 3, style='F')
            
            rows = [("Tensão do Banco:", f"{fmt_br(d['tensao_banco'], 0)} V"), ("Capacidade das Baterias:", f"{fmt_br(d['capacidade_bateria'], 0)} Ah"), ("Capacidade Total Armazenada:", f"{fmt_br(d['cap_total_kwh'], 2)} kWh"), ("Energia Útil Disponível (com DoD):", f"{fmt_br(d['energia_util'], 2)} kWh"),("Autonomia Estimada:", f"{fmt_br(d['autonomia_horas'], 0)} horas")]
            pdf.set_y(ty); rh = 12; clw = 90; cvw = 70
            for l, v in rows:
                pdf.set_x(tx); pdf.set_fill_color(225, 225, 225); pdf.set_font("Arial", 'B', 10); pdf.cell(clw, rh, limpar_texto(l), 0, 0, 'R', fill=True)
                pdf.set_fill_color(245, 245, 245); pdf.set_font("Arial", '', 10); pdf.cell(cvw, rh, limpar_texto(f"   {v}"), 0, 1, 'L', fill=True)
            pdf.rounded_rect(tx, ty, 160, 60, 3, style='D')

            # PAG 3 - Equipamentos e Final
            pdf.add_page(); pdf.ln(35); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, limpar_texto("2 - EQUIPAMENTOS E INVESTIMENTO"), ln=True); pdf.ln(10)
            pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, limpar_texto("2.1 Composição do Sistema Híbrido:"), ln=True); pdf.set_font("Arial", '', 10)
            
            ki = [f"01 {d['inversor_nome'].upper()} (Tecnologia Anti-Ilhamento e Backup)", f"01 {d['bateria_nome'].upper()} ({fmt_br(d['capacidade_bateria'], 0)}Ah em {fmt_br(d['tensao_banco'], 0)}V)", "01 Materiais de Instalação e Proteção (String Box, Disjuntores DC/AC)", "01 Mão de Obra Especializada e Homologação (ART)"]
            for it in ki:
                if pdf.get_y() > 270: pdf.add_page()
                cx, cy = pdf.get_x() + 15, pdf.get_y() + 3
                pdf.line(cx, cy-1.5, cx+1.5, cy); pdf.line(cx+2.5, cy, cx, cy+1.5); pdf.line(cx, cy+1.5, cx-1.5, cy); pdf.line(cx-2.5, cy, cx, cy-1.5)
                pdf.set_x(30); pdf.multi_cell(0, 6, limpar_texto(it), align='L'); pdf.ln(5)

            if d['img_inversor'] and os.path.exists(d['img_inversor']):
                pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("Imagem do Inversor Híbrido Selecionado"), ln=True, align='C'); x_img = (210-80)/2; pdf.image(d['img_inversor'], x=x_img, w=80)

            pdf.ln(15); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, limpar_texto("2.2 Resumo Financeiro:"), ln=True); pdf.ln(5)
            def drow(txt, val):
                if pdf.get_y() > 270: pdf.add_page()
                pdf.set_font("Arial", '', 10); cx, cy = pdf.get_x() + 5, pdf.get_y() + 5
                pdf.line(cx, cy-1.5, cx+1.5, cy); pdf.line(cx+1.5, cy, cx, cy+1.5); pdf.line(cx, cy+1.5, cx-1.5, cy); pdf.line(cx-1.5, cy, cx, cy-1.5)
                pdf.set_x(20); w_label = pdf.get_string_width(txt); pdf.cell(w_label + 2, 10, limpar_texto(txt), 0, 0)
                w_val = pdf.get_string_width(val); w_dots = 170 - w_label - w_val - 5
                if w_dots > 0: dw = pdf.get_string_width("."); nd = int(w_dots / dw); pdf.cell(w_dots, 10, "." * nd, 0, 0, 'C')
                pdf.cell(w_val, 10, val, 0, 1, 'R')

            val_tot = fmt_br(d['preco_final'], 2); drow("Sistema Completo (Inversor Híbrido, Baterias e Instalação)", f"R$ {val_tot}")
            pdf.ln(15); pdf.set_font("Arial", 'B', 14); lbl_tot = "VALOR TOTAL DO INVESTIMENTO R$: "; w_lbl = pdf.get_string_width(lbl_tot); w_val = pdf.get_string_width(val_tot)
            pdf.set_x(210 - 20 - w_lbl - w_val); pdf.cell(w_lbl, 10, limpar_texto(lbl_tot), 0, 0, 'L'); pdf.set_font("Arial", '', 14); pdf.cell(w_val, 10, val_tot, 0, 1, 'L')
            
            if pdf.get_y() > 250: pdf.add_page()
            pdf.ln(20); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, limpar_texto("3 – VALIDAÇÃO DA PROPOSTA"), ln=True); pdf.ln(10)
            line_width = 140; x_line = (210 - line_width) / 2; pdf.line(x_line, pdf.get_y(), x_line + line_width, pdf.get_y()); pdf.ln(2)
            
            x_sig = (210 - 80) / 2
            def sign_line(lbl, val):
                pdf.set_font("Arial", 'B', 10); pdf.cell(15, 5, lbl, 0, 0, 'R'); pdf.set_font("Arial", '', 10); pdf.cell(0, 5, limpar_texto(val), 0, 1, 'L')
            pdf.set_x(x_sig); sign_line("Nome:", "Gustavo de Oliveira Silva"); pdf.set_x(x_sig); sign_line("Cargo:", "Responsável técnico"); pdf.set_x(x_sig); sign_line("CPF:", "113.185.936-70")

            nome_arq = f"{num_prop_str}-{d['nome']}-Hibrido.pdf"; folder_path = db.get_config('pdf_path')
            if kivy_platform == "android":
                if folder_path and os.path.exists(folder_path): out_path = os.path.join(folder_path, nome_arq)
                else:
                    try: from android.storage import primary_external_storage_path; out_path = os.path.join(primary_external_storage_path(), 'Download', nome_arq)
                    except: out_path = nome_arq
                pdf.output(out_path); Clock.schedule_once(lambda dt: toast(f"Salvo em: {out_path}"))
            else:
                if folder_path and os.path.exists(folder_path): nome_arq = os.path.join(folder_path, nome_arq)
                pdf.output(nome_arq)
                try: os.startfile(nome_arq)
                except: pass
                Clock.schedule_once(lambda dt: toast("PDF Híbrido Gerado!"))

            try: prox_num = int(num_prop_str) + 1; db.set_config('num_proposta', str(prox_num)); self.root.ids.config_num_prop.text = str(prox_num)
            except: pass
        except Exception as e: Clock.schedule_once(lambda dt: toast(f"Erro PDF: {str(e)}"))

if __name__ == "__main__":
    Window.softinput_mode = "below_target"
    SolarApp().run()