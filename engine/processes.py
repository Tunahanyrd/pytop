# processes.py
import psutil
import threading
import time
from typing import List, Dict, Any

class ProcessManager:
    def __init__(self, interval: float = 1.0, attrs: List[str] = None, ad_value: Any = None):
        self.interval = interval
        self.attrs = attrs or [
            'pid', 'name', 'username',
            'cpu_percent', 'memory_percent',  # zaten vardı
            'ppid', 'status', 'nice', 'num_threads', 'create_time', 'cmdline'
        ]
        # Erişim hatalarında döngü kırılmasın
        self.ad_value = "-" if ad_value is None else ad_value

        self._processes: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = threading.Thread(target=self._update_loop, daemon=True)

    def _take_snapshot(self):
        """Tek seferlik snapshot al ve atomik yaz."""
        snapshot: List[Dict[str, Any]] = []
        # ad_value verildiği için çoğu hata değer ile doldurulur;
        # yine de garanti için try/except ile devam et.
        for proc in psutil.process_iter(attrs=self.attrs, ad_value=self.ad_value):
            try:
                snapshot.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        with self._lock:
            self._processes[:] = snapshot

    def start(self):
        """Update process list in background"""
        if not self._thread.is_alive():
            self._thread = threading.Thread(target=self._update_loop, daemon=True)

        if self._running:
            return
        self._running = True

        # cold start
        for _ in range(2):
            for _ in psutil.process_iter(attrs=self.attrs, ad_value=self.ad_value):
                pass
        time.sleep(1)

        self._take_snapshot()

        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._thread.join()

    def _update_loop(self):
        while self._running:
            self._take_snapshot()
            time.sleep(self.interval)
    
    def get_processes(self) -> List[Dict[str, Any]]:
        """
        Instant process list.
        changing the returned list does not affect the main list.
        """
        with self._lock:
            return list(self._processes) # return its copy
    
    def sort_processes(self, 
                       by:str="cpu_percent", 
                       reverse:bool=True) -> List[Dict[str, Any]]:
        procs = self.get_processes()
        return sorted(procs, key=lambda p: (p.get(by, 0) is None, p.get(by, 0), p.get("pid", 0)), reverse=reverse)
    
    def filter_by_user(self, uname:str) -> List[Dict[str, any]]:
        return [p for p in self.get_processes() if p.get("username") == uname]
    
    def __call__(self,
                 *,
                 sort_by: str = "cpu_percent",
                 reverse: bool = True,
                 limit: int | None = None,
                 fields: list[str] | None = None,
                 user: str | None = None,
                 formatters: dict[str, callable] | None = None) -> list[dict]:
        """
        Kullanım: pm(sort_by="cpu_percent", limit=20, fields=[...], formatters={...})
        - sort_by/reverse: sıralama
        - limit: ilk N kayıt
        - fields: sadece bu alanları sırayla döndür
        - user: belli kullanıcıya filtrele
        - formatters: {"cpu_percent": fn, "memory_percent": fn, ...} alan bazlı formatter
        """
        procs = self.sort_processes(by=sort_by, reverse=reverse)
        
        if user:
            procs = [p for p in procs if p.get("username") == user]
        if limit is not None and limit >= 0:
            procs = procs[:limit]
        if fields:
            projected = []
            for p in procs:
                row = {k: p.get(k) for k in fields}
                projected.append(row)
            procs = projected
        if formatters:
            out = []
            for p in procs:
                q = {}
                for k,v in p.items():
                    fmt = formatters.get(k)
                    try:
                        q[k] = fmt(v) if fmt else v
                    except Exception:
                        q[k] = v
                out.append(q)
            procs = out
        return procs
    
    @staticmethod
    def default_formatters(parser) -> dict:
        """İstersen hızlıca tak-çalıştır formatter seti."""
        return {
            "cpu_percent":  lambda v: parser.format_percent(v or 0.0, part=""),
            "memory_percent": lambda v: parser.format_percent(v or 0.0, part=""),
            "rss": lambda b: parser.format_bytes(b or 0),
            "vms": lambda b: parser.format_bytes(b or 0),
            "read_bytes": lambda b: parser.format_bytes(b or 0),
            "write_bytes": lambda b: parser.format_bytes(b or 0),
            "create_time": lambda t: parser.format_ctime(t),
        }