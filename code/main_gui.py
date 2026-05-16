import re
import tkinter as tk
from tkinter import ttk, messagebox

def run_round_robin(processes, quantum):
    procs = [{'pid': p['pid'], 'arrival': p['arrival'], 'burst': p['burst'], 'remaining': p['burst'], 'start_time': -1, 'finish': 0} for p in processes]
    procs.sort(key=lambda x: (x['arrival'], x['pid']))
    queue, gantt, queue_states, time, done, n, visited = [], [], [], 0, 0, len(procs), [False] * len(procs)

    for i, p in enumerate(procs):
        if p['arrival'] <= time: queue.append(i); visited[i] = True

    while done < n:
        if not queue:
            time = min(p['arrival'] for i, p in enumerate(procs) if not visited[i])
            for i, p in enumerate(procs):
                if not visited[i] and p['arrival'] <= time: queue.append(i); visited[i] = True
            continue

        idx = queue.pop(0)
        p = procs[idx]
        if p['start_time'] == -1: p['start_time'] = time
        run_time = min(quantum, p['remaining'])

        queue_states.append({
            'at_time': time,
            'running': p['pid'],
            'waiting': [procs[i]['pid'] for i in queue],
        })

        gantt.append({'pid': p['pid'], 'start': time, 'end': time + run_time})
        time += run_time
        p['remaining'] -= run_time

        for i, proc in enumerate(procs):
            if not visited[i] and proc['arrival'] <= time: queue.append(i); visited[i] = True

        if p['remaining'] == 0: p['finish'] = time; done += 1
        else: queue.append(idx)

    total_wt = total_tat = total_rt = 0
    results = []
    for p in procs:
        tat, wt, rt = p['finish'] - p['arrival'], (p['finish'] - p['arrival']) - p['burst'], p['start_time'] - p['arrival']
        total_wt += wt; total_tat += tat; total_rt += rt
        results.append({'pid': p['pid'], 'arrival': p['arrival'], 'burst': p['burst'], 'wt': wt, 'tat': tat, 'rt': rt})

    return gantt, results, {'avg_wt': round(total_wt/n, 2), 'avg_tat': round(total_tat/n, 2), 'avg_rt': round(total_rt/n, 2)}, queue_states

def run_srtf(processes):
    n, remaining, start_t, finish_t = len(processes), [p['burst'] for p in processes], [-1]*len(processes), [0]*len(processes)
    t, completed, gantt, current = 0, 0, [], -1

    while completed < n:
        idx, min_time = -1, float('inf')
        for i in range(n):
            if processes[i]['arrival'] <= t and 0 < remaining[i] < min_time:
                min_time, idx = remaining[i], i
        
        if idx == -1: t += 1; continue
        if start_t[idx] == -1: start_t[idx] = t
        
        if current != idx: gantt.append({'pid': processes[idx]['pid'], 'start': t, 'end': t + 1}); current = idx
        else: gantt[-1]['end'] += 1
        
        remaining[idx] -= 1; t += 1
        if remaining[idx] == 0: finish_t[idx] = t; completed += 1

    total_wt = total_tat = total_rt = 0
    results = []
    for i in range(n):
        tat, wt, rt = finish_t[i] - processes[i]['arrival'], (finish_t[i] - processes[i]['arrival']) - processes[i]['burst'], start_t[i] - processes[i]['arrival']
        total_wt += wt; total_tat += tat; total_rt += rt
        results.append({'pid': processes[i]['pid'], 'arrival': processes[i]['arrival'], 'burst': processes[i]['burst'], 'wt': wt, 'tat': tat, 'rt': rt})

    return gantt, results, {'avg_wt': round(total_wt/n, 2), 'avg_tat': round(total_tat/n, 2), 'avg_rt': round(total_rt/n, 2)}

class SchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("C2 — Round Robin vs SRTF")
        self.root.geometry("720x900")
        self.processes = []
        self.sections = {} 
        
        self.main_canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scroll_frame = tk.Frame(self.main_canvas)
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.bind("<Configure>", lambda e: self.main_canvas.itemconfig(self.main_canvas.find_withtag("all")[0], width=e.width))
        self.main_canvas.bind_all("<MouseWheel>", lambda e: self.main_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._build_ui()

    def _build_ui(self):
        sf = self.scroll_frame
        
        inp = tk.LabelFrame(sf, text=" Input ", font=("Arial", 10, "bold"))
        inp.pack(fill="x", padx=10, pady=5)
        self.entries = {}
        fields = [("Process ID", "pid"), ("Arrival Time", "arrival"), ("Burst Time", "burst"), ("Time Quantum", "quantum")]
        for col, (lbl, key) in enumerate(fields):
            tk.Label(inp, text=lbl).grid(row=0, column=col, padx=8, pady=5)
            e = tk.Entry(inp, width=12); e.grid(row=1, column=col, padx=8, pady=5)
            self.entries[key] = e

        bf = tk.Frame(sf); bf.pack(pady=5)
        for txt, cmd, color in [("Add Process", self._add_process, "#58D05C"), (" Delete Selected", self._delete_selected, "#1E4543"), ("Clear All", self._clear_all, "#cd2114"), (" Run Both", self._run, "#277EC6")]:
            tk.Button(bf, text=txt, command=cmd, bg=color, fg="white", width=14).pack(side="left", padx=5)

        self.proc_table = self._make_table(sf, " Processes ", ("PID", "Arrival", "Burst"), 4)
        
        for name, key, color in [("Round Robin", "rr", "#2196F3"), ("SRTF", "srtf", "#9C27B0")]:
            lf = tk.LabelFrame(sf, text=f" {name} ", font=("Arial", 10, "bold"), fg=color)
            lf.pack(fill="x", padx=10, pady=5)
            cv = tk.Canvas(lf, width=650, height=70, bg="white"); cv.pack(pady=5)
            tbl = self._make_table(lf, None, ("PID", "Arrival", "Burst", "WT", "TAT", "RT"), 5)
            lbls = self._make_avg_row(lf)
            rq_tbl = None
            if key == "rr":
                rq_frame = tk.LabelFrame(lf, text=" Ready Queue ", font=("Arial", 9, "bold"))
                rq_frame.pack(fill="x", padx=5, pady=3)
                rq_tbl = ttk.Treeview(rq_frame, columns=("At Time", "Running", "Waiting"), show="headings", height=4)
                rq_tbl.heading("At Time", text="At Time")
                rq_tbl.heading("Running", text="Running")
                rq_tbl.heading("Waiting", text=" Ready Queue")
                rq_tbl.column("At Time", width=80,  anchor="center")
                rq_tbl.column("Running", width=100, anchor="center")
                rq_tbl.column("Waiting", width=440, anchor="w")
                rq_tbl.pack(fill="x", padx=5, pady=3)
            self.sections[key] = {'canvas': cv, 'table': tbl, 'lbls': lbls, 'rq': rq_tbl}

    
        cmp = tk.LabelFrame(sf, text=" Comparison Summary ", font=("Arial", 10, "bold"), fg="#F44336")
        cmp.pack(fill="x", padx=10, pady=5)
        self.cmp_table = ttk.Treeview(cmp, columns=("Metric", "Round Robin", "SRTF"), show="headings", height=3)
        for c in ("Metric", "Round Robin", "SRTF"): self.cmp_table.heading(c, text=c); self.cmp_table.column(c, width=200, anchor="center")
        self.cmp_table.pack(pady=5)

        conc = tk.LabelFrame(sf, text=" Conclusion ", font=("Arial", 10, "bold"), fg="#795548")
        conc.pack(fill="x", padx=10, pady=5)
        self.conc_txt = tk.Text(conc, width=80, height=12, font=("Arial", 9), state="disabled", bg="#FAFAFA", wrap="word")
        self.conc_txt.pack(pady=5)

    def _make_table(self, parent, title, cols, height):
        if title:
            parent = tk.LabelFrame(parent, text=title, font=("Arial", 10, "bold"))
            parent.pack(fill="x", padx=10, pady=5)
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
        for c in cols: tree.heading(c, text=c); tree.column(c, width=100, anchor="center")
        tree.pack(pady=5)
        return tree

    def _make_avg_row(self, parent):
        frame = tk.Frame(parent); frame.pack(anchor="w", padx=10, pady=5)
        lbls = {}
        for i, (text, key, color) in enumerate([("Avg WT:", 'wt', "#2196F3"), ("Avg TAT:", 'tat', "#4CAF50"), ("Avg RT:", 'rt', "#FF9800")]):
            tk.Label(frame, text=text, font=("Arial", 10)).grid(row=0, column=i*2, padx=5)
            lbls[key] = tk.Label(frame, text="—", font=("Arial", 10, "bold"), fg=color)
            lbls[key].grid(row=0, column=i*2+1, padx=5)
        return lbls

    def _add_process(self):
        pid, arr, brst = [self.entries[k].get().strip() for k in ("pid", "arrival", "burst")]
        errors = []

        if not pid or not arr or not brst: errors.append("- Missing required fields.")
        if pid and not re.fullmatch(r'[Pp]\d+', pid): errors.append("- ID must be P<number> (e.g. P1).")
        if pid.upper() in [p["pid"] for p in self.processes]: errors.append(f"- Duplicate ID: {pid}.")
        if arr and (not arr.isdigit() or int(arr) < 0): errors.append("- Arrival Time must be a valid positive number or 0.")
        if brst and (not brst.isdigit() or int(brst) <= 0): errors.append("- Burst Time must be a valid number > 0.")

        if errors:
            messagebox.showerror("Validation Errors", "Please fix the following issues:\n" + "\n".join(errors))
            return

        self.processes.append({"pid": pid.upper(), "arrival": int(arr), "burst": int(brst)})
        self.proc_table.insert("", "end", values=(pid.upper(), arr, brst))
        for k in ("pid", "arrival", "burst"): self.entries[k].delete(0, tk.END)

    def _run(self):
        if not self.processes: return messagebox.showwarning("Warning", "Add at least one process.")
        q_str = self.entries["quantum"].get().strip()
        
        if not q_str or not q_str.isdigit() or int(q_str) <= 0:
            return messagebox.showerror("Validation Error", "Time Quantum must be a valid number > 0.")
        
        quantum = int(q_str)
        rr_g, rr_r, rr_a, rr_qs = run_round_robin(self.processes, quantum)
        sr_g, sr_r, sr_a = run_srtf(self.processes)

        self._populate(self.sections['rr'],   rr_g, rr_r, rr_a, rr_qs)
        self._populate(self.sections['srtf'], sr_g, sr_r, sr_a, None)
        
        self.cmp_table.delete(*self.cmp_table.get_children())
        for lbl, k in [("Avg Waiting Time", 'avg_wt'), ("Avg Turnaround Time", 'avg_tat'), ("Avg Response Time", 'avg_rt')]:
            self.cmp_table.insert("", "end", values=(lbl, rr_a[k], sr_a[k]))
            
        self._generate_conclusion(rr_a, sr_a, rr_r, sr_r, quantum)

    def _populate(self, sec, gantt, res, avg, queue_states=None):
        sec['canvas'].delete("all")
        for row in sec['table'].get_children(): sec['table'].delete(row)
        for r in res: sec['table'].insert("", "end", values=(r["pid"], r["arrival"], r["burst"], r["wt"], r["tat"], r["rt"]))
        for k in ('wt', 'tat', 'rt'): sec['lbls'][k].config(text=str(avg[f'avg_{k}']))

        if sec['rq'] is not None:
            for row in sec['rq'].get_children(): sec['rq'].delete(row)
            if queue_states:
                for state in queue_states:
                    waiting_str = " → ".join(state['waiting']) if state['waiting'] else "—"
                    sec['rq'].insert("", "end", values=(f"t = {state['at_time']}", state['running'], waiting_str))
        
        if not gantt: return
        tt, CW, XO, colors = gantt[-1]["end"], 640, 5, ["#4FC3F7","#81C784","#FFB74D","#E57373","#BA68C8"]
        cmap = {p: colors[i % len(colors)] for i, p in enumerate(dict.fromkeys(s["pid"] for s in gantt))}
        for s in gantt:
            x1, x2 = XO + (s["start"]/tt)*CW, XO + (s["end"]/tt)*CW
            sec['canvas'].create_rectangle(x1, 5, x2, 45, fill=cmap[s["pid"]], outline="white", width=2)
            sec['canvas'].create_text((x1+x2)/2, 25, text=s["pid"], font=("Arial", 9, "bold"))
            sec['canvas'].create_text(x1, 57, text=str(s["start"]), font=("Arial", 8))
        sec['canvas'].create_text(XO+CW, 57, text=str(tt), font=("Arial", 8))

    def _generate_conclusion(self, rr_a, sr_a, rr_r, sr_r, q):
        def cmp(r, s, m): 
            return f"RR is better on {m}" if r < s else f"SRTF is better on {m}" if s < r else f"Both are Equal on {m}"
        
        rr_rng = max(x['wt'] for x in rr_r) - min(x['wt'] for x in rr_r)
        sr_rng = max(x['wt'] for x in sr_r) - min(x['wt'] for x in sr_r)
        fairness = "RR was fairer (smaller WT gap between processes)." if rr_rng <= sr_rng else "SRTF was fairer here."
        efficiency = "SRTF was more efficient (Lower Avg TAT)." if sr_a['avg_tat'] < rr_a['avg_tat'] else "RR was more efficient."

        max_burst = max(x['burst'] for x in rr_r)
        if q >= max_burst:
            q_effect = f"Q={q} is very large (>= max burst {max_burst}), making RR act exactly like FCFS (No slicing)."
        else:
            q_effect = f"Q={q} caused frequent time-slicing, improving responsiveness but adding context switch overhead."

        shortest_job = min(sr_r, key=lambda x: x['burst'])
        longest_job = max(sr_r, key=lambda x: x['burst'])
        srtf_adv = f"Yes, the shortest job ({shortest_job['pid']}) waited {shortest_job['wt']}s, while the longest ({longest_job['pid']}) waited {longest_job['wt']}s."

        txt = (
            f"--- Required Comparison Focus ---\n\n"
            f"• Fairness vs Efficiency:\n  {fairness} VS {efficiency}\n\n"
            f"• Time Slicing vs Shortest-Job Preference:\n  RR's time slicing shares CPU fairly among all, while SRTF minimizes overall waiting by prioritizing shorter jobs.\n\n"
            f"• Effect on First Response Time:\n  {cmp(rr_a['avg_rt'], sr_a['avg_rt'], 'First Response Time (Avg RT)')}.\n\n"
            f"• Effect of Quantum Size on RR:\n  {q_effect}\n\n"
            f"• Does SRTF give strong advantage to short jobs?:\n  {srtf_adv}"
        )
        
        self.conc_txt.config(state="normal")
        self.conc_txt.delete("1.0", tk.END)
        self.conc_txt.insert(tk.END, txt)
        self.conc_txt.config(state="disabled")

    def _delete_selected(self):
        selected_item = self.proc_table.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a process from the table first.")
            return
            
        item_id = selected_item[0]
        item_values = self.proc_table.item(item_id, 'values')
        selected_pid = item_values[0]
        
        self.processes = [p for p in self.processes if p['pid'] != selected_pid]
        self.proc_table.delete(item_id)

    def _clear_all(self):
        self.processes.clear()
        for k in self.entries: self.entries[k].delete(0, tk.END)
        for tbl in [self.proc_table, self.sections['rr']['table'], self.sections['srtf']['table'], self.cmp_table]:
            for row in tbl.get_children(): tbl.delete(row)
        if self.sections['rr']['rq'] is not None:
            for row in self.sections['rr']['rq'].get_children(): self.sections['rr']['rq'].delete(row)
        for sec in self.sections.values():
            sec['canvas'].delete("all")
            for lbl in sec['lbls'].values(): lbl.config(text="—")
        self.conc_txt.config(state="normal"); self.conc_txt.delete("1.0", tk.END); self.conc_txt.config(state="disabled")

