from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict, List, Dict, Optional, Literal, Tuple
from abc import ABC, abstractmethod
from enum import Enum

# ===== ham veri için returnler =====
class CpuCoreFreqTD(TypedDict, total=False):
    current: float
    min: Optional[float]
    max: Optional[float]
    
class CpuSnapshotTD(TypedDict):
    percent_total: float
    percent_percpu: List[float]
    freq_percpu: List[CpuCoreFreqTD]

class MemorySnapshotTD(TypedDict):
    total: int
    available: int
    used: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float

class DiskPartitionUsageTD(TypedDict):
    mountpoint: str
    total: int
    used: int
    free: int
    percent: float

class DiskIoTD(TypedDict):
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int

class DiskSnapshotTD(TypedDict):
    usage: List[DiskPartitionUsageTD]
    io_perdisk: Dict[str, DiskIoTD]

class ProcessInfoTD(TypedDict, total=False):
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    
class SeverityLevel(str, Enum):
    OK   = "ok"
    INFO = "info"   
    WARN = "warn"
    CRIT = "crit"
# ===== ui a gidecek normalize veri =====

class CpuViewTD(TypedDict, total=False):
    total_text: str
    total_severity: Literal["ok", "warn", "crit"]
    per_core_text: List[str]
    per_core_severity: List[Literal["ok", "warn", "crit"]]
    freq_text: List[str]

class MemoryViewTD(TypedDict, total=False):
    used_text: str
    total_text: str
    percent_text: str
    percent_severity: Literal["ok", "warn", "crit"]
    swap_used_text: str
    swap_total_text: str
    swap_percent_text: str
    swap_severity: Literal["ok", "warn", "crit"]

class DiskUsageRowTD(TypedDict, total=False):
    mountpoint: str
    used_text: str
    total_text: str
    percent_text: str
    severity: Literal["ok", "warn", "crit"]

class DiskIoViewTD(TypedDict, total=False):
    # disk adı -> özet metinler / hızlar
    per_disk: Dict[str, Dict[str, str]]

class ProcessRowTD(TypedDict, total=False):
    pid: int
    name: str
    user: str
    cpu_text: str
    mem_text: str
    cpu_value: float
    mem_value: float

# ===== state =====

@dataclass
class ParserConfig:
    profiles: Dict[str, SeverityProfile] = field(default_factory=dict)
    shorten_len: int = 24
    percent_decimals: int = 1
    use_binary_units: bool = True  # True -> KiB/MiB/GiB, False -> KB/MB/GB

@dataclass
class ParserState:
    # IO hızları için önceki sayaçlar
    last_io_bytes: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # name -> (read_bytes, write_bytes)
    last_ts: Optional[float] = None
    # Process stabilizasyonu vs. için de alan açılabilir
    # e.g., last_procs: Dict[int, ProcessRowTD] = field(default_factory=dict)

@dataclass(frozen=True)
class SeverityBand:
    min_inclusive: float
    max_exclusive: float
    label: SeverityLevel
    
@dataclass
class SeverityProfile:
    name: str
    bands: List[SeverityBand] = field(default_factory=list)
    clamp: Tuple[float, float] = (0.0, 100.0)
    higher_is_worse: bool = True
    
    def validate(self) -> None:
        eps = 1e-9
        
        lo, hi = self.clamp
        if not (lo < hi):
            raise ValueError(f"[{self.name}] invalid clamp: {self.clamp} (lo < hi olmalı)")
        if not self.bands:
            raise ValueError(f"[{self.name}] bands boş olamaz")
        
        bands = sorted(self.bands, key=lambda b: (b.min_inclusive, b.max_exclusive))
        if abs(bands[0].min_inclusive - lo) > eps:
            raise ValueError(
                f"[{self.name}] ilk band {bands[0].min_inclusive}’den başlıyor; clamp.min={lo} ile uyumsuz"
            )
        prev_max = lo
        for i, b in enumerate(bands):
            # min < max şartı
            if not (b.min_inclusive + eps < b.max_exclusive):
                raise ValueError(
                    f"[{self.name}] band#{i} min>=max: {b.min_inclusive} .. {b.max_exclusive}"
                )

            # clamp içinde mi?
            if b.min_inclusive < lo - eps or b.max_exclusive > hi + eps:
                raise ValueError(
                    f"[{self.name}] band#{i} clamp dışına taşıyor: {b.min_inclusive} .. {b.max_exclusive}, clamp={self.clamp}"
                )

            # boşluk/çakışma kontrolü: yeni band, tam olarak prev_max’ten başlamalı
            if abs(b.min_inclusive - prev_max) > eps:
                if b.min_inclusive > prev_max + eps:
                    # boşluk var
                    raise ValueError(
                        f"[{self.name}] band boşluğu: {prev_max} .. {b.min_inclusive}"
                    )
                else:
                    # çakışma var
                    raise ValueError(
                        f"[{self.name}] band çakışması: {b.min_inclusive} < {prev_max}"
                    )

            prev_max = b.max_exclusive

        # son band clamp.max’e kadar uzanmalı
        if abs(prev_max - hi) > eps:
            raise ValueError(
                f"[{self.name}] son band clamp.max’e kadar gitmiyor: son={prev_max}, clamp.max={hi}"
            )
    
def make_default_config() -> ParserConfig:
    bands = [
        SeverityBand(0.0, 50.0,  SeverityLevel.OK),
        SeverityBand(50.0, 75.0, SeverityLevel.INFO),
        SeverityBand(75.0, 85.0, SeverityLevel.WARN),
        SeverityBand(85.0, 101.0, SeverityLevel.CRIT),  # 100'ü kapsasın diye 101
    ]

    cpu_profile  = SeverityProfile(name="cpu_percent",  bands=bands, clamp=(0.0, 100.0), higher_is_worse=True)
    mem_profile  = SeverityProfile(name="mem_percent",  bands=bands, clamp=(0.0, 100.0), higher_is_worse=True)
    disk_profile = SeverityProfile(name="disk_percent", bands=bands, clamp=(0.0, 100.0), higher_is_worse=True)

    # validate hepsini
    cpu_profile.validate()
    mem_profile.validate()
    disk_profile.validate()

    cfg = ParserConfig(
        profiles={
            "cpu": cpu_profile,
            "mem": mem_profile,
            "disk": disk_profile,
        },
        shorten_len=24,
        percent_decimals=1,
        use_binary_units=True,
    )
    return cfg

# ===== parser =====

class Parser(ABC):
    """
    engine verilerini ui için uygun hale getirme
    """
    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()
        self.state = ParserState()

    # ---- Yardımcı/biçimleyici ----
    @abstractmethod
    def format_bytes(self, value: int) -> str:
        """Birim dönüştür (B -> KiB/MiB/GiB veya KB/MB/GB), string döndür."""
        pass

    @abstractmethod
    def format_percent(self, value: float, decimals: Optional[int] = None) -> str:
        """Yüzdeyi belirtilen ondalıkla biçimle (örn. '57.3%')."""
        pass

    @abstractmethod
    def format_freq(self, mhz: float) -> str:
        """Frekansı kullanıcı dostu (MHz/GHz) metne çevir."""
        pass

    @abstractmethod
    def severity_from_percent(self, value: float, warn: float, crit: float) -> Literal["ok", "warn", "crit"]:
        """Yüzde değerine göre ok/warn/crit etiketi belirle."""
        pass
    
    def severity_for(self, metric: Literal["cpu", "mem", "disk"], value: float) -> SeverityLevel:
        profile = self.config.profiles.get(metric)
        if profile is None:
            return SeverityLevel.OK
        return self.severity_from_percent(value, profile)
    
    @abstractmethod
    def shorten_path(self, path: str, max_len: Optional[int] = None) -> str:
        """Metni (örn. mountpoint) kısalt; baş/son koru, ortadan kes."""
        pass
  
class SimpleParse(Parser):
       
    def format_bytes(self, value: int) -> str:
        units = ["B", "KiB", "MiB", "GiB", "TiB"] if self.config.use_binary_units else ["B", "KB", "MB", "GB", "TB"]
        step = 1024 if self.config.use_binary_units else 1000
          
        num = float(value) 
        for unit in units:
              if abs(num) < step:
                  return f"{num:.1f} {unit}"
              else:
                  num /= step
        return f"{num:.1f} {units[-1]}"
            
    def format_percent(self, value: List[float], 
                       decimals: Optional[int] = None,
                       part: str = "CPU: "):          
        if decimals == None:
            decimals = self.config.percent_decimals
        if isinstance(value, (int, float)):
            return f"{part}{max(0.0, min(100.0, round(value, decimals)))}%"
        return [f"{part}{idx}: {max(0.0, min(100.0, round(v, decimals)))}%" for idx, v in enumerate(value)]    
    
    def format_freq(self, mhz: Optional[float]) -> str:
        units = ["MHz", "GHz"]
        for unit in units:
            if abs(mhz) < 1000:
                return f"{round(mhz, 2)} MHz"
            else:
                return f"{round((mhz / 1000), 2)} GHz"
            
    def severity_from_percent(self, value: float, profile: SeverityProfile) -> SeverityLevel:
        lo, hi = profile.clamp      
        v = min(max(value, lo), hi)
        if not profile.higher_is_worse:
            v = hi - (v - lo)
        for band in profile.bands:
            if band.min_inclusive <= v < band.max_exclusive:
                return band.label
        return profile.bands[-1].label
    def shorten_path(self, path, max_len = None):
        r"""
        Uzun dosya yolunu kısaltır.
        Öncelik sırası:
        1) Yol zaten kısa ise: dokunma.
        2) İlk iki segment + son iki segment + '…' ile dene.
        3) Hâlâ uzunsa: klasik head…tail karakter kesme.
        4) max_len çok küçükse: sadece dosya adı ya da mümkün olan en kısa form.

        Destekler:
        - UNIX absolute: /usr/lib/...
        - Windows drive: C:\Users\...
        - UNC: \\server\share\dir\file
        - Home: ~/dir/file veya ~\dir\file
        - Göreli yollar: dir/sub/dir/file

        Notlar:
        - Orijinal ayıraç ('/' veya '\') çoğunluğa göre korunur.
        - Ellipsis unicode '…' (1 char). İstersen '...' kullan.
        """
        s = path if isinstance(path, str) else str(path)
        if max_len <= 0:
            return ""
        if len(s) <= max_len:
            return s
        if "\\" in s and "/" not in s:
            orig_sep = "\\"
        else:
            orig_sep = "/"
        norm = s.replace("\\", "/")
        prefix = ""
        rest = norm
        
        if norm.startswith("//"):
            parts = norm.split("/")
            if len(parts) > 4:
                prefix = "//" + parts[2] + "/" + parts[3]
                rest = "/" + "/".join(parts[4:])
            else:
                prefix = ""
                rest = norm   
        elif len(norm) >= 2 and norm[1] == ":" and norm[0].isalpha():
            prefix = norm[:2]  # "C:"
            if len(norm) >= 3 and norm[2] in ("/",):
                rest = norm[2:]
            else:
                rest = norm[2:]
        # Absolute root: /
        elif norm.startswith("/"):
            prefix = "/"
            rest = norm[1:]
        # Home: ~/
        elif norm.startswith("~/"):
            prefix = "~"
            rest = norm[2:]
        # Home (Windows style): ~\
        elif norm.startswith("~\\"):
            prefix = "~"
            rest = norm[2:]
        else:
            # prefix yok
            prefix = ""
            rest = norm

        # Çoklu slash'ları sıkıştır
        rest = "/".join([p for p in rest.split("/") if p != ""])

        # Parçalara ayır
        parts = [p for p in rest.split("/") if p] if rest else []

        # Kısa ise (prefix + / + join(parts)) döndür
        def reassemble(pfx: str, segs: list[str]) -> str:
            if pfx in ("", "~"):
                out = (pfx + ("/" if pfx and segs else "") + "/".join(segs)) if segs else pfx
            elif pfx.startswith("//"):  # UNC
                out = pfx + ("/" + "/".join(segs) if segs else "")
            elif len(pfx) == 2 and pfx.endswith(":"):  # Drive
                out = pfx + ("/" + "/".join(segs) if segs else "")
            else:
                out = (pfx + "/") if pfx else ""
                out += "/".join(segs)
            # Orijinal ayıracı geri koy
            return out.replace("/", orig_sep)

        full_norm = reassemble(prefix, parts)
        if len(full_norm) <= max_len:
            return full_norm

        # Segment sayısı 4'ten azsa: "ilk-iki son-iki" anlamlı değil -> head…tail'e düşeceğiz
        if len(parts) >= 4:
            # 1) İlk iki + son iki + ellipsis
            head = parts[:2]
            tail = parts[-2:]
            mid = ["..."]  # UI tarafında üç nokta path'te daha güvenli olabilir
            # (istersen '…' da koyabilirsin)
            candidate = reassemble(prefix, head + mid + tail)
            if len(candidate) <= max_len:
                return candidate

            # 2) Dosya adına öncelik: son segment tam kalsın, baştan mümkün olduğunca çok göster
            fname = parts[-1]
            base = reassemble(prefix, ["..."] + [fname])
            if len(base) <= max_len:
                return base
            # Eğer hâlâ uzunsa: dosya adı çok uzun olabilir; filename'i de kırpacağız
            if len(fname) > 6 and max_len > len(prefix) + 5:  # min biraz alan kalsın
                # filename'i baş/son koruyarak kısalt
                keep = max_len - (len(prefix.replace("/", orig_sep)) + len(orig_sep) + 3)  # '.../'
                keep = max(3, keep)  # min 3 char
                left = keep // 2
                right = keep - left
                short_fname = fname[:left] + "…" + fname[-right:] if keep < len(fname) else fname
                candidate2 = reassemble(prefix, ["..."] + [short_fname])
                if len(candidate2) <= max_len:
                    return candidate2

        # 3) Klasik karakter bazlı head…tail (en son çare)
        #   full_norm zaten orijinal ayıracı içeriyor.
        #   Çok küçük max_len koruması:
        if max_len <= len(ellipsis) + 1:
            # sığdığı kadar ellipsis
            return (ellipsis if len(ellipsis) <= max_len else ellipsis[:max_len])

        keep = max_len - len(ellipsis)
        left = max(1, keep // 2)
        right = max(1, keep - left)
        squeezed = full_norm[:left] + ellipsis + full_norm[-right:]

        # Garanti: aşarsa buda
        if len(squeezed) > max_len:
            squeezed = squeezed[:max_len]

        return squeezed
    
        
        
        
            
    