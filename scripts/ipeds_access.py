"""Export selected tables from the IPEDS Access database.

Fall Enrollment 2024 lives in the 2024-25 Access file, not as a standalone
EF2024A.zip. This helper downloads that Access zip, uses Jackcess (Java) to
write CSVs, and caches them under /tmp so a refresh can re-run.
"""
from __future__ import annotations

import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

CACHE = Path("/tmp/pioneer-ipeds")
ACCESS_ZIP = (
    "https://nces.ed.gov/ipeds/tablefiles/zipfiles/IPEDS_2024-25_Provisional.zip"
)
JARS = {
    "jackcess-4.0.8.jar": (
        "https://repo1.maven.org/maven2/com/healthmarketscience/jackcess/"
        "jackcess/4.0.8/jackcess-4.0.8.jar"
    ),
    "commons-lang3-3.17.0.jar": (
        "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/"
        "3.17.0/commons-lang3-3.17.0.jar"
    ),
    "commons-logging-1.3.5.jar": (
        "https://repo1.maven.org/maven2/commons-logging/commons-logging/"
        "1.3.5/commons-logging-1.3.5.jar"
    ),
}
EXPORT_JAVA = r"""
import com.healthmarketscience.jackcess.Database;
import com.healthmarketscience.jackcess.DatabaseBuilder;
import com.healthmarketscience.jackcess.Table;
import com.healthmarketscience.jackcess.Column;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
public class IpedsExportTable {
  static String csv(Object v) {
    if (v == null) return "";
    String s = String.valueOf(v);
    if (s.contains(",") || s.contains("\"") || s.contains("\n"))
      return "\"" + s.replace("\"", "\"\"") + "\"";
    return s;
  }
  public static void main(String[] args) throws Exception {
    Database db = DatabaseBuilder.open(new File(args[0]));
    Table t = db.getTable(args[1]);
    PrintWriter w = new PrintWriter(new FileWriter(args[2]));
    boolean first = true;
    for (Column c : t.getColumns()) {
      if (!first) w.print(",");
      w.print(csv(c.getName()));
      first = false;
    }
    w.println();
    int n = 0;
    for (var row : t) {
      first = true;
      for (Column c : t.getColumns()) {
        if (!first) w.print(",");
        w.print(csv(row.get(c.getName())));
        first = false;
      }
      w.println();
      n++;
    }
    w.close();
    db.close();
    System.out.println("wrote " + n + " rows to " + args[2]);
  }
}
"""
UA = "PioneerDataLabs/1.0 (vintage refresh; +https://datalabsai.netlify.app)"


def _fetch(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as resp:
        dest.write_bytes(resp.read())
    return dest


def export_table(table_name: str) -> Path:
    """Return a CSV path for one Access table, exporting when needed."""
    CACHE.mkdir(parents=True, exist_ok=True)
    csv_path = CACHE / f"{table_name}.csv"
    if csv_path.exists() and csv_path.stat().st_size > 1000:
        return csv_path
    jar_dir = CACHE / "jars"
    for name, url in JARS.items():
        _fetch(url, jar_dir / name)
    zip_path = _fetch(ACCESS_ZIP, CACHE / "IPEDS_2024-25_Provisional.zip")
    accdb = CACHE / "IPEDS202425.accdb"
    if not accdb.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extract("IPEDS202425.accdb", CACHE)
    java_src = CACHE / "IpedsExportTable.java"
    java_src.write_text(EXPORT_JAVA, encoding="utf-8")
    jars = ":".join(str(p) for p in sorted(jar_dir.glob("*.jar")))
    if not jars:
        sys.exit("FATAL: Jackcess jars failed to download")
    try:
        subprocess.check_call(["javac", "-cp", jars, str(java_src)], cwd=CACHE)
    except FileNotFoundError:
        sys.exit("FATAL: javac is required to read the IPEDS 2024-25 Access database")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"FATAL: javac failed for IPEDS export ({exc})")
    try:
        subprocess.check_call(
            [
                "java", "-cp", f"{CACHE}:{jars}", "IpedsExportTable",
                str(accdb), table_name, str(csv_path),
            ],
            cwd=CACHE,
        )
    except FileNotFoundError:
        sys.exit("FATAL: java is required to read the IPEDS 2024-25 Access database")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"FATAL: Jackcess export of {table_name} failed ({exc})")
    if not csv_path.exists() or csv_path.stat().st_size < 1000:
        sys.exit(f"FATAL: IPEDS export wrote an empty {csv_path}")
    return csv_path
