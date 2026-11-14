"""Import generated synthetic insurance CSV files into the project's SQLite database.
Run from the project root: python scripts/import_insurance_data.py
"""
import csv
from pathlib import Path
from sqlalchemy import inspect, select, func
from backend.app.database import Base, SessionLocal, engine
from backend.app.models import entities

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'generated'
TABLES = [
    ('claimants.csv', entities.Claimant),
    ('policies.csv', entities.Policy),
    ('incidents.csv', entities.Incident),
    ('providers.csv', entities.Provider),
    ('claims.csv', entities.Claim),
    ('invoices.csv', entities.Invoice),
    ('payments.csv', entities.Payment),
    ('relationship_edges.csv', entities.RelationshipEdge),
]

def main():
    missing = [name for name, _ in TABLES if not (DATA_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError('Missing CSV files: ' + ', '.join(missing))
    Base.metadata.create_all(bind=engine)
    with SessionLocal.begin() as session:
        for filename, model in TABLES:
            path = DATA_DIR / filename
            cols = {column.name: column for column in inspect(model).columns}
            primary_keys = [c.name for c in inspect(model).primary_key]
            if len(primary_keys) != 1:
                raise RuntimeError(f'{model.__tablename__} needs one primary key')
            pk = primary_keys[0]
            with path.open(newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or pk not in reader.fieldnames:
                    raise ValueError(f'{filename}: missing primary key column {pk}')
                unknown = set(reader.fieldnames) - set(cols)
                if unknown:
                    print(f'{filename}: ignoring extra columns {sorted(unknown)}')
                rows = []
                for row in reader:
                    item = {}
                    for name, col in cols.items():
                        if name not in row or row[name] == '':
                            continue
                        value = row[name]
                        try:
                            if col.type.python_type is float:
                                value = float(value)
                            elif col.type.python_type is int:
                                value = int(value)
                            elif col.type.python_type is bool:
                                value = value.lower() in ('true', '1', 'yes')
                        except NotImplementedError:
                            pass
                        item[name] = value
                    rows.append(item)
            existing = set(session.scalars(select(getattr(model, pk))).all())
            new_rows = [r for r in rows if r[pk] not in existing]
            if new_rows:
                session.bulk_insert_mappings(model, new_rows)
            print(f'{model.__tablename__}: {len(new_rows)} imported, {len(rows) - len(new_rows)} already present')
    print('Import complete. Refresh http://127.0.0.1:8000/api/claims?limit=5')

if __name__ == '__main__':
    main()
