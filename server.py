#!/usr/bin/env python3
"""
Teto — Backend Server
Serves the site + API for saving leads to SQLite.
Usage: python3 server.py
"""

import http.server
import json
import sqlite3
import os
import datetime
import hashlib

DB_PATH = os.environ.get('TETO_DB', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'teto.db'))
PORT = int(os.environ.get('PORT', 8080))

# ─── Database Setup ───────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        status TEXT DEFAULT 'novo',

        -- Dados Pessoais
        nome TEXT,
        cpf TEXT,
        nascimento TEXT,
        email TEXT,
        celular TEXT,
        estado_civil TEXT,
        ocupacao TEXT,
        renda_bruta REAL,
        compor_renda TEXT,
        renda_composta REAL,
        renda_total REAL,
        uf TEXT,

        -- Dados do Imóvel
        tipo_imovel TEXT,
        cep TEXT,
        cidade TEXT,
        bairro TEXT,
        endereco TEXT,
        valor_imovel REAL,
        ano_construcao INTEGER,
        area REAL,
        quartos TEXT,
        vagas TEXT,
        situacao_imovel TEXT,
        perc_quitado TEXT,
        titularidade TEXT,
        matricula TEXT,
        iptu TEXT,

        -- Crédito
        valor_desejado REAL,
        valor_aprovado REAL,
        prazo INTEGER,
        finalidade TEXT,
        restricao_cpf TEXT,

        -- Resultado Análise
        score_credito INTEGER,
        status_analise TEXT,
        ltv REAL,
        taxa_mensal REAL,
        cet REAL,
        primeira_parcela REAL,
        comprometimento REAL,

        -- Raw JSON (backup completo)
        raw_json TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS lead_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id TEXT NOT NULL,
        event TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (lead_id) REFERENCES leads(id)
    )''')

    conn.commit()
    conn.close()
    print(f"[DB] SQLite ready at {DB_PATH}")


def generate_id():
    ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    h = hashlib.md5(ts.encode()).hexdigest()[:6].upper()
    return f"TC-{h}"


def save_lead(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    lead_id = generate_id()
    now = datetime.datetime.now().isoformat()

    renda = data.get('rendaBruta', 0) or 0
    rc = data.get('rendaComposta', 0) or 0
    rt = renda + rc

    vi = data.get('valorImovel', 0) or 0
    vd = data.get('valorDesejado', 0) or 0
    va = min(vd, vi * 0.6)

    c.execute('''INSERT INTO leads VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    )''', (
        lead_id, now, 'novo',
        data.get('nome'), data.get('cpf'), data.get('nascimento'),
        data.get('email'), data.get('celular'), data.get('estadoCivil'),
        data.get('ocupacao'), renda, data.get('comporRenda'),
        rc, rt, data.get('uf'),
        data.get('tipoImovel'), data.get('cep'), data.get('cidade'),
        data.get('bairro'), data.get('endereco'), vi,
        data.get('anoConstrucao'), data.get('area'),
        data.get('quartos'), data.get('vagas'),
        data.get('situacaoImovel'), data.get('percQuitado'),
        data.get('titularidade'), data.get('matricula'), data.get('iptu'),
        vd, va, data.get('prazo'),
        data.get('finalidade'), data.get('restricaoCpf'),
        data.get('scoreCredito'), data.get('statusAnalise'),
        data.get('ltv'), data.get('taxaMensal'),
        data.get('cet'), data.get('parcela1'),
        data.get('comprometimento'),
        json.dumps(data, ensure_ascii=False)
    ))

    c.execute('INSERT INTO lead_events (lead_id, event, details, created_at) VALUES (?,?,?,?)',
              (lead_id, 'lead_created', 'Lead criado via simulador', now))

    conn.commit()
    conn.close()
    print(f"[LEAD] Saved {lead_id} — {data.get('nome')} — {data.get('email')}")
    return lead_id


def get_all_leads():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM leads ORDER BY created_at DESC')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_lead(lead_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM leads WHERE id = ?', (lead_id,))
    row = c.fetchone()
    c.execute('SELECT * FROM lead_events WHERE lead_id = ? ORDER BY created_at', (lead_id,))
    events = [dict(r) for r in c.fetchall()]
    conn.close()
    if row:
        lead = dict(row)
        lead['events'] = events
        return lead
    return None


def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM leads')
    total = c.fetchone()[0]
    c.execute('SELECT COALESCE(SUM(valor_aprovado),0) FROM leads')
    volume = c.fetchone()[0]
    c.execute('SELECT COALESCE(AVG(score_credito),0) FROM leads WHERE score_credito IS NOT NULL')
    avg_score = c.fetchone()[0]
    c.execute('SELECT COALESCE(AVG(taxa_mensal),0) FROM leads WHERE taxa_mensal IS NOT NULL')
    avg_taxa = c.fetchone()[0]
    c.execute('SELECT COALESCE(AVG(ltv),0) FROM leads WHERE ltv IS NOT NULL')
    avg_ltv = c.fetchone()[0]
    c.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
    by_status = dict(c.fetchall())
    c.execute("SELECT finalidade, COUNT(*) FROM leads GROUP BY finalidade")
    by_finalidade = dict(c.fetchall())
    c.execute("SELECT uf, COUNT(*) FROM leads GROUP BY uf")
    by_uf = dict(c.fetchall())
    conn.close()
    return {
        'total_leads': total,
        'volume_total': volume,
        'score_medio': round(avg_score, 1),
        'taxa_media': round(avg_taxa * 100, 2) if avg_taxa else 0,
        'ltv_medio': round(avg_ltv, 1),
        'por_status': by_status,
        'por_finalidade': by_finalidade,
        'por_uf': by_uf
    }


# ─── HTTP Server ──────────────────────────────────────────────────

class TetoHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/api/leads':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                lead_id = save_lead(data)
                self.send_json(201, {'ok': True, 'id': lead_id})
            except Exception as e:
                self.send_json(400, {'ok': False, 'error': str(e)})
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_GET(self):
        if self.path == '/api/leads':
            leads = get_all_leads()
            self.send_json(200, {'leads': leads, 'count': len(leads)})
        elif self.path.startswith('/api/leads/'):
            lead_id = self.path.split('/')[-1]
            lead = get_lead(lead_id)
            if lead:
                self.send_json(200, lead)
            else:
                self.send_json(404, {'error': 'Lead not found'})
        elif self.path == '/api/stats':
            stats = get_stats()
            self.send_json(200, stats)
        else:
            super().do_GET()

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        if '/api/' in (args[0] if args else ''):
            print(f"[API] {args[0]}")


if __name__ == '__main__':
    init_db()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(('0.0.0.0', PORT), TetoHandler)
    print(f"\n🏠 Teto server running at http://localhost:{PORT}")
    print(f"   Site:  http://localhost:{PORT}/index.html")
    print(f"   API:   http://localhost:{PORT}/api/leads")
    print(f"   Stats: http://localhost:{PORT}/api/stats\n")
    server.serve_forever()
