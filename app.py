#PDF Merger Using Python

import os
import sys
import threading
import time
import traceback
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
except Exception:
    raise RuntimeError("ttk_bootstrap is required. Install  ttk_bootstrap")

from PyPDF2 import PdfReader, PdfMerger

# Optional OS drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TDND_AVAILABLE = True
except Exception:
    TDND_AVAILABLE = False

APP_TITLE = "PDF Merger App "

def ts():
    return datetime.now().strftime("%H:%M:%S")

class PDFFile:
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.pages = None
        self.status = "Unknown"  


class PremiumPDFMerger:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1000x660")
        self.root.minsize(880, 540)

        # flatly styling
        self.style = tb.Style(theme="flatly")

        # Data accessing 
        self.files: list[PDFFile] = []

        # UI build
        self._build_header()
        self._build_main()
        self._build_footer()

        # dnd
        self._setup_os_dnd()

        self._drag_data = {"item": None}


    def _build_header(self):
        header = ttk.Frame(self.root)
        header.pack(side="top", fill="x")


        self.banner = tk.Canvas(header, height=110, highlightthickness=0)
        self.banner.pack(fill="x")
        self._draw_gradient(self.banner, "#2c7fb8", "#1f5f9a")

        x0, y0 = 22, 18
        self.banner.create_oval(x0, y0, x0+74, y0+74, fill="#ffffff", outline="", stipple="")
        self.banner.create_polygon(60, 30, 36, 60, 84, 60, fill="#2c7fb8", outline="")
        self.banner.create_text(120, 46, anchor="w", text="PDF Merger", font=("Segoe UI", 20, "bold"), fill="white")
        self.banner.create_text(120, 70, anchor="w", text="Fast • Clean • Secure", font=("Segoe UI", 10), fill="#dbeefd")

    def _draw_gradient(self, canvas, color1, color2):
        """Simple vertical gradient fill"""
        canvas.update_idletasks()
        w = canvas.winfo_reqwidth() or self.root.winfo_width() or 900
        h = 110
    
        r1, g1, b1 = self._hex_to_rgb(color1)
        r2, g2, b2 = self._hex_to_rgb(color2)
        steps = 80
        for i in range(steps):
            r = int(r1 + (r2 - r1) * (i / steps))
            g = int(g1 + (g2 - g1) * (i / steps))
            b = int(b1 + (b2 - b1) * (i / steps))
            hexc = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_rectangle((i * (w / steps), 0, (i + 1) * (w / steps), h), outline=hexc, fill=hexc)

    def _hex_to_rgb(self, hx):
        hx = hx.lstrip("#")
        return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

    def _build_main(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        left_card = tb.Frame(main, bootstyle="light", padding=(12, 12, 12, 12))
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        left_title = ttk.Label(left_card, text="PDF Files", font=("Segoe UI", 12, "bold"))
        left_title.pack(anchor="w")

        cols = ("filename", "pages", "status")
        self.tree = ttk.Treeview(left_card, columns=cols, show="headings", selectmode="extended", height=20)
        self.tree.heading("filename", text="Filename")
        self.tree.heading("pages", text="Pages")
        self.tree.heading("status", text="Status")
        self.tree.column("filename", anchor="w", width=480)
        self.tree.column("pages", anchor="center", width=80)
        self.tree.column("status", anchor="center", width=120)
        self.tree.pack(fill="both", expand=True, pady=(8, 10))

        # scroll
        vsb = ttk.Scrollbar(left_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")

        #  toolbar 
        toolbar = ttk.Frame(left_card)
        toolbar.pack(fill="x", pady=(0, 6))

        btn_add = ttk.Button(toolbar, text="➕ Add PDFs", bootstyle="primary", command=self.add_files)
        btn_add.pack(side="left", padx=4)
        btn_dnd_hint = ttk.Label(toolbar, text="(or drag files here)", font=("Segoe UI", 9))
        btn_dnd_hint.pack(side="left", padx=(6, 4))

        btn_remove = ttk.Button(toolbar, text="🗑️ Remove", bootstyle="danger-outline", command=self.remove_selected)
        btn_remove.pack(side="left", padx=4)
        btn_clear = ttk.Button(toolbar, text="🧹 Clear All", bootstyle="warning-outline", command=self.clear_all)
        btn_clear.pack(side="left", padx=4)

        btn_up = ttk.Button(toolbar, text="▲ Move Up", bootstyle="secondary", command=lambda: self.move_selected(-1))
        btn_up.pack(side="right", padx=4)
        btn_down = ttk.Button(toolbar, text="▼ Move Down", bootstyle="secondary", command=lambda: self.move_selected(1))
        btn_down.pack(side="right", padx=4)

# details and merging

        right_card = tb.Frame(main, bootstyle="light", padding=(12, 12, 12, 12), width=320)
        right_card.pack(side="right", fill="y")

        details_title = ttk.Label(right_card, text="Details & Actions", font=("Segoe UI", 12, "bold"))
        details_title.pack(anchor="w")

        self.details_box = tk.Text(right_card, height=12, state="disabled", font=("Segoe UI", 10), wrap="word")
        self.details_box.pack(fill="both", expand=False, pady=(8, 10))

        merge_frame = ttk.Frame(right_card)
        merge_frame.pack(fill="x", pady=(4, 8))

        self.merge_btn = ttk.Button(merge_frame, text="💾 Merge PDFs", bootstyle="success", command=self.start_merge)
        self.merge_btn.pack(fill="x", pady=(0, 6))

        # progress & spinner
        self.progress = ttk.Progressbar(right_card, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(6, 4))
        self.spinner = tb.Button(right_card, text="⏳", bootstyle="info", state="disabled")
        self.spinner.pack_forget()

    
        help_label = ttk.Label(right_card, text="Activity Log", font=("Segoe UI", 10, "bold"))
        help_label.pack(anchor="w", pady=(10, 0))
        self.log = tk.Text(right_card, height=8, state="disabled", font=("Segoe UI", 9))
        self.log.pack(fill="both", expand=True, pady=(6, 0))

        # Event
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._open_selected_file)

        self.tree.bind("<ButtonPress-1>", self._on_tree_press)
        self.tree.bind("<B1-Motion>", self._on_tree_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_release)

    # Footer

    def _build_footer(self):
        footer = ttk.Frame(self.root)
        footer.pack(side="bottom", fill="x")
        footer_label = ttk.Label(footer, text="Tip: You can reorder files by dragging inside the list, or use Move Up/Down.", font=("Segoe UI", 9))
        footer_label.pack(side="left", padx=12, pady=8)

    # files

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF files", "*.pdf")])
        if not paths:
            return
        self._add_paths(paths)

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if not os.path.isfile(p) or not p.lower().endswith(".pdf"):
                continue
            if any(f.path == p for f in self.files):
                self._log(f"{ts()} • Skipped duplicate: {p}")
                continue
            fileobj = PDFFile(p)
        
            try:
                reader = PdfReader(p)
                if getattr(reader, "is_encrypted", False):
                    try:
                        reader.decrypt("")
                        fileobj.pages = len(reader.pages)
                        fileobj.status = "Encrypted (decrypted)"
                    except Exception:
                        fileobj.pages = None
                        fileobj.status = "Encrypted"
                else:
                    fileobj.pages = len(reader.pages)
                    fileobj.status = "OK"
            except Exception as e:
                fileobj.pages = None
                fileobj.status = "Corrupt"
                self._log(f"{ts()} • Validation error for {fileobj.name}: {e}")
            self.files.append(fileobj)
            added += 1
        if added:
            self._rebuild_tree()
            self._log(f"{ts()} • Added {added} PDF(s).")
            self._update_status(f"Added {added} file(s)")

    def _rebuild_tree(self):

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for f in self.files:
            pages = str(f.pages) if f.pages is not None else "-"
            self.tree.insert("", "end", values=(f.name, pages, f.status))

    def clear_all(self):
        if not self.files:
            return
        if not messagebox.askyesno("Clear", "Remove all files from the list?"):
            return
        self.files.clear()
        self._rebuild_tree()
        self._log(f"{ts()} • Cleared file list.")
        self._update_status("Ready")
        self.progress["value"] = 0
        self._clear_details()

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Remove", "Select file(s) to remove.")
            return
        
        items = list(self.tree.get_children())
        removed = 0
        for iid in reversed(sel):  
            idx = items.index(iid)
            del self.files[idx]
            self.tree.delete(iid)
            removed += 1
        self._log(f"{ts()} • Removed {removed} file(s).")
        self._update_status("Updated list")
        self._clear_details()

    def move_selected(self, direction: int):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        items = list(self.tree.get_children())
        idx = items.index(iid)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(items):
            return
        # swap data
        self.files[idx], self.files[new_idx] = self.files[new_idx], self.files[idx]
        self._rebuild_tree()
        new_iid = self.tree.get_children()[new_idx]
        self.tree.selection_set(new_iid)
        self.tree.see(new_iid)
        self._update_status("Order updated")

   
    def _on_tree_press(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self._drag_data["item"] = iid

    def _on_tree_motion(self, event):
        if not self._drag_data["item"]:
            return
        over = self.tree.identify_row(event.y)
        if over and over != self._drag_data["item"]:
            items = list(self.tree.get_children())
            src = items.index(self._drag_data["item"])
            dst = items.index(over)
            item_obj = self.files.pop(src)
            self.files.insert(dst, item_obj)
            self._rebuild_tree()
            self._drag_data["item"] = self.tree.get_children()[dst]
            self.tree.selection_set(self._drag_data["item"])

    def _on_tree_release(self, event):
        self._drag_data = {"item": None}

    #  details and selection

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            self._clear_details()
            return
        iid = sel[0]
        idx = list(self.tree.get_children()).index(iid)
        f = self.files[idx]
        self._show_details(f)

    def _show_details(self, f: PDFFile):
        self.details_box.configure(state="normal")
        self.details_box.delete("1.0", "end")
        info = [
            f"Filename: {f.name}",
            f"Full path: {f.path}",
            f"Pages: {f.pages if f.pages is not None else 'Unknown'}",
            f"Status: {f.status}",
            "",
            "Double-click list item to open file in your default PDF viewer.",
        ]
        self.details_box.insert("1.0", "\n".join(info))
        self.details_box.configure(state="disabled")

    def _clear_details(self):
        self.details_box.configure(state="normal")
        self.details_box.delete("1.0", "end")
        self.details_box.configure(state="disabled")

    def _open_selected_file(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        idx = list(self.tree.get_children()).index(iid)
        f = self.files[idx]
        try:
            if sys.platform.startswith("win"):
                os.startfile(f.path)
            elif sys.platform == "darwin":
                os.system(f'open "{f.path}"')
            else:
                os.system(f'xdg-open "{f.path}"')
        except Exception as e:
            self._log(f"{ts()} • Failed to open {f.name}: {e}")

    
    # OS drag & drop setup

    def _setup_os_dnd(self):
        if not TDND_AVAILABLE:
            self._log(f"{ts()} • OS drag-and-drop not available (install tkinterdnd2 optionally).")
            return
        try:
           
            if hasattr(self.root, "drop_target_register"):
                self.tree.drop_target_register(DND_FILES)
                self.tree.dnd_bind("<<Drop>>", self._on_files_dropped)
            else:
                self._log(f"{ts()} • Root does not support TkinterDnD drop registration.")
        except Exception as e:
            self._log(f"{ts()} • Failed to enable OS DnD: {e}")

    def _on_files_dropped(self, event):
        try:
            data = self.root.tk.splitlist(event.data)
            paths = [p for p in data if p.lower().endswith(".pdf") and os.path.isfile(p)]
            if not paths:
                self._log(f"{ts()} • No PDF files found in dropped items.")
                return
            self._add_paths(paths)
        except Exception as e:
            self._log(f"{ts()} • DnD error: {e}")


    # Merge logic

    def start_merge(self):
        if not self.files:
            messagebox.showinfo("Merge", "No PDF files added.")
            return
        dest = filedialog.asksaveasfilename(title="Save merged PDF", defaultextension=".pdf",
                                            filetypes=[("PDF files", "*.pdf")], initialfile="merged.pdf")
        if not dest:
            return
       
        self.merge_btn.configure(state="disabled")
        self.spinner.configure(state="normal")
        self.spinner.place_forget()
    
        self.spinner.pack(fill="x", pady=(6, 0))
        self.progress["value"] = 0
        thread = threading.Thread(target=self._merge_worker, args=(dest,), daemon=True)
        thread.start()

    def _merge_worker(self, dest_path):
        try:
            self._log(f"{ts()} • Merge started -> {dest_path}")
            merger = PdfMerger()
            total = len(self.files)
            processed = 0
            skipped = 0

            for idx, f in enumerate(self.files):
                self._log(f"{ts()} • Processing: {f.name} (status={f.status})")
                if str(f.status).lower().startswith("corrupt"):
                    self._log(f"{ts()} • Skipping corrupt: {f.name}")
                    skipped += 1
                else:
                    try:
                        reader = PdfReader(f.path)
                        if getattr(reader, "is_encrypted", False):
                            try:
                                reader.decrypt("")
                            except Exception:
                                self._log(f"{ts()} • Could not decrypt {f.name}; skipping.")
                                skipped += 1
                                continue
                        merger.append(reader)
                        self._log(f"{ts()} • Appended: {f.name}")
                    except Exception as e:
                        self._log(f"{ts()} • Error appending {f.name}: {e}")
                        skipped += 1
                processed += 1
                pct = int((processed / total) * 100)
                self.root.after(0, lambda v=pct: self.progress.configure(value=v))
                self._update_status(f"Merging... ({processed}/{total})")
                time.sleep(0.08)  

            if processed == 0:
                raise RuntimeError("No files processed.")

            with open(dest_path, "wb") as out:
                merger.write(out)
            merger.close()

            self._log(f"{ts()} • Merge completed. Output: {dest_path}")
            self._update_status("Merge completed")
            messagebox.showinfo("Merge Completed", f"Merged PDF saved to:\n{dest_path}")

        except Exception as e:
            self._log(f"{ts()} • Merge failed: {e}")
            self._log(traceback.format_exc())
            self._update_status("Merge failed")
            messagebox.showerror("Merge Failed", f"An error occurred:\n{e}")
        finally:

            self.root.after(0, lambda: self.progress.configure(value=100))
            self.root.after(300, lambda: self.progress.configure(value=0))
            self.root.after(300, lambda: self.merge_btn.configure(state="normal"))
            self.root.after(300, lambda: (self.spinner.configure(state="disabled"), self.spinner.pack_forget()))

    def _update_status(self, text):
        self.root.title(f"{APP_TITLE} — {text}")

    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main():
    
    if TDND_AVAILABLE:
        try:
            root = TkinterDnD.Tk()
        except Exception:
            root = tk.Tk()
    else:
        root = tk.Tk()

    app = PremiumPDFMerger(root)
    root.mainloop()

if __name__ == "__main__":
    main()

