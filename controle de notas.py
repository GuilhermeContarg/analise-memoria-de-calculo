import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class NotasApp:
    def __init__(self, master):
        self.master = master
        master.title("Controle de Notas Escolares")

        self.conn = sqlite3.connect('notas.db')
        self.cursor = self.conn.cursor()
        self._criar_tabelas()

        # Configurar estilo
        style = ttk.Style()
        style.theme_use("clam") # tema base que permite customização
        style.configure("Treeview", background="#E6F7FF", fieldbackground="#E6F7FF", foreground="black")
        style.configure("Treeview.Heading", background="#0073E6", foreground="white")

        # Widget Treeview
        self.tree = ttk.Treeview(master, columns=("Materia", "1", "2", "3", "4", "Media"), show="headings", height=8)
        self.tree.grid(row=5, columnspan=6)
        self.tree.heading("Materia", text="Matéria")
        self.tree.heading("1", text="1º Bimestre")
        self.tree.heading("2", text="2º Bimestre")
        self.tree.heading("3", text="3º Bimestre")
        self.tree.heading("4", text="4º Bimestre")
        self.tree.heading("Media", text="Média Final")
        self.atualizar_tabela()

        tk.Label(master, text="Materia").grid(row=0)
        tk.Label(master, text="Bimestre").grid(row=1)
        tk.Label(master, text="Nota").grid(row=2)

        self.materia = tk.Entry(master)
        self.bimestre = tk.Entry(master)
        self.nota = tk.Entry(master)

        self.materia.grid(row=0, column=1)
        self.bimestre.grid(row=1, column=1)
        self.nota.grid(row=2, column=1)

        self.submit_button = tk.Button(master, text="Salvar Nota", command=self.salvar_nota)
        self.submit_button.grid(row=3, columnspan=2)

        self.calcular_media_button = tk.Button(master, text="Calcular Média", command=self.calcular_media)
        self.calcular_media_button.grid(row=4, columnspan=2)

    def _criar_tabelas(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia TEXT,
                bimestre INTEGER,
                nota REAL
            );
        ''')
        self.conn.commit()

    def salvar_nota(self):
        materia = self.materia.get()
        bimestre = int(self.bimestre.get())
        nota = float(self.nota.get())
        self.cursor.execute('INSERT INTO notas (materia, bimestre, nota) VALUES (?, ?, ?)', (materia, bimestre, nota))
        self.conn.commit()
        self.atualizar_tabela()

    def atualizar_tabela(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.cursor.execute('SELECT materia, bimestre, nota FROM notas ORDER BY materia, bimestre')
        rows = self.cursor.fetchall()
        materias = sorted(set(row[0] for row in rows))
        for materia in materias:
            notas = ['-' for _ in range(4)]
            notas_reais = []
            for row in rows:
                if row[0] == materia:
                    notas[row[1]-1] = str(row[2])
                    notas_reais.append(row[2])
            if notas_reais:
                media = sum(notas_reais) / len(notas_reais)
            else:
                media = '-'
            self.tree.insert("", tk.END, values=(materia, notas[0], notas[1], notas[2], notas[3], f"{media:.2f}" if isinstance(media, float) else "-"))

    def calcular_media(self):
        self.cursor.execute('SELECT AVG(nota) FROM notas')
        media = self.cursor.fetchone()[0]
        messagebox.showinfo("Média das Notas", f"A média das notas é: {media:.2f}")

def main():
    root = tk.Tk()
    app = NotasApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
