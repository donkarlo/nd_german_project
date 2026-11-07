import sqlite3, sys
from pathlib import Path
sys.path.insert(0,"/home/donkarlo/Dropbox/repo/nd_german_project/src/nd_german")
import dictionary_core
p="/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3"
c=sqlite3.connect(p)
c.execute("PRAGMA foreign_keys=ON")
row=c.execute("SELECT entry_index,raw FROM entries WHERE headword=? ORDER BY entry_index DESC LIMIT 1",("In- und Ausland",)).fetchone()
if not row: raise RuntimeError("Entry not found")
idx,raw=row
old="In- und Ausland (feste Wortverbindung):"
new="In- und Ausland (Phrase):"
if old in raw:
    raw=raw.replace(old,new,1)
e=dictionary_core.parse_entry(raw)
assert e.role=="phrase", (e.role,e.first_line)
c.execute("BEGIN IMMEDIATE")
c.execute("UPDATE entries SET raw=?,first_line=?,headword=?,role=?,translation=?,headword_norm=?,lexeme_norm=?,translation_norm=?,search_norm=? WHERE entry_index=?",(e.raw,e.first_line,e.headword,e.role,e.translation,e.headword_norm,e.lexeme_norm,e.translation_norm,e.search_norm,idx))
c.execute("DELETE FROM entries_fts WHERE rowid=?",(idx,))
c.execute("INSERT INTO entries_fts (rowid,headword_norm,lexeme_norm,translation_norm,search_norm) VALUES (?,?,?,?,?)",(idx,e.headword_norm,e.lexeme_norm,e.translation_norm,e.search_norm))
c.execute("DELETE FROM verb_valency_entries WHERE entry_key=?",("verb|in und ausland",))
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('verb_rektion_dirty','0')")
c.commit()
print("CORRECTED:",idx,e.headword,e.role)
print("ENTRY COUNT:",c.execute("SELECT COUNT(*) FROM entries").fetchone()[0])
print("FTS COUNT:",c.execute("SELECT COUNT(*) FROM entries_fts").fetchone()[0])
print("BAD VALENCY:",c.execute("SELECT COUNT(*) FROM verb_valency_entries WHERE headword_norm=?",(e.headword_norm,)).fetchone()[0])
print("PAUSE VALENCY:",c.execute("SELECT entry_key,is_phrase FROM verb_valency_entries WHERE headword_norm=?",(dictionary_core.normalize_text("Pause machen"),)).fetchall())
print("FOREIGN KEY:",c.execute("PRAGMA foreign_key_check").fetchall())
print("INTEGRITY:",c.execute("PRAGMA integrity_check").fetchone()[0])
c.close()
