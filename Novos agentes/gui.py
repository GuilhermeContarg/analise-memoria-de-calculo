import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading
import os
from main import run_system

class AgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Multi-Agente - Seletor de Arquivos")
        self.root.geometry("600x450")

        # --- Source Selection ---
        self.source_var = tk.StringVar(value="LOCAL")
        
        frame_source = tk.LabelFrame(root, text="Origem dos Dados", padx=10, pady=10)
        frame_source.pack(fill="x", padx=10, pady=5)

        rb_local = tk.Radiobutton(frame_source, text="Pasta Local", variable=self.source_var, value="LOCAL", command=self.toggle_source)
        rb_local.pack(anchor="w")

        rb_drive = tk.Radiobutton(frame_source, text="Google Drive (ID da Pasta)", variable=self.source_var, value="DRIVE", command=self.toggle_source)
        rb_drive.pack(anchor="w")

        # --- Path/ID Input ---
        frame_input = tk.Frame(root)
        frame_input.pack(fill="x", padx=10, pady=5)

        self.lbl_path = tk.Label(frame_input, text="Caminho da Pasta:")
        self.lbl_path.pack(side="left")

        self.entry_path = tk.Entry(frame_input, width=50)
        self.entry_path.pack(side="left", padx=5)

        self.btn_browse = tk.Button(frame_input, text="Selecionar", command=self.browse_folder)
        self.btn_browse.pack(side="left")

        # --- Export Options ---
        frame_export = tk.LabelFrame(root, text="Opções de Exportação", padx=10, pady=10)
        frame_export.pack(fill="x", padx=10, pady=5)
        
        self.var_export_local = tk.BooleanVar(value=True)
        self.chk_local = tk.Checkbutton(frame_export, text="Salvar no Computador (Download)", variable=self.var_export_local)
        self.chk_local.pack(anchor="w")
        
        self.var_export_drive = tk.BooleanVar(value=False)
        self.chk_drive = tk.Checkbutton(frame_export, text="Salvar no Google Drive", variable=self.var_export_drive)
        self.chk_drive.pack(anchor="w")

        self.var_export_github = tk.BooleanVar(value=False)
        self.chk_github = tk.Checkbutton(frame_export, text="Upload para GitHub", variable=self.var_export_github)
        self.chk_github.pack(anchor="w")

        # --- Run Button ---
        self.btn_run = tk.Button(root, text="EXECUTAR SISTEMA", bg="green", fg="white", font=("Arial", 10, "bold"), command=self.start_execution)
        self.btn_run.pack(pady=10)

        # --- Log Area ---
        self.txt_log = scrolledtext.ScrolledText(root, height=12)
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=5)

        # Initial State
        self.toggle_source()

    def toggle_source(self):
        source = self.source_var.get()
        if source == "LOCAL":
            self.lbl_path.config(text="Caminho da Pasta:")
            self.btn_browse.config(state="normal")
        else:
            self.lbl_path.config(text="ID da Pasta Drive:")
            self.btn_browse.config(state="disabled")

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, folder_selected)

    def log(self, message):
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)

    def start_execution(self):
        # Run in a separate thread to not freeze GUI
        thread = threading.Thread(target=self.run_process)
        thread.start()

    def run_process(self):
        self.btn_run.config(state="disabled")
        self.txt_log.delete(1.0, tk.END)
        self.log("Iniciando processamento...")

        source = self.source_var.get()
        path_id = self.entry_path.get().strip()
        exp_local = self.var_export_local.get()
        exp_drive = self.var_export_drive.get()
        exp_github = self.var_export_github.get()
        
        if not path_id:
            messagebox.showwarning("Aviso", "Por favor, especifique o Caminho ou ID.")
            self.btn_run.config(state="normal")
            return

        try:
            # Call the main orchestrator with a custom logger so logs appear in GUI
            result = run_system(
                source_type=source, 
                path_or_id=path_id, 
                export_local=exp_local,
                export_drive=exp_drive,
                export_github=exp_github,
                logger_func=self.log
            )
            self.log(f"Finalizado: {result}")
            if result == "Success":
                messagebox.showinfo("Sucesso", "Processamento concluído com sucesso!")
            else:
                messagebox.showerror("Erro", "Ocorreu um erro durante o processamento.")
        except Exception as e:
            self.log(f"Erro Crítico: {e}")
            messagebox.showerror("Erro Crítico", str(e))
        finally:
            self.btn_run.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = AgentGUI(root)
    root.mainloop()
