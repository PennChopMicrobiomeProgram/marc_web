"""Utility script to create a synthetic MARC test database.

The generated database is intended for local development and UI testing.
"""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from marc_db.models import (
    Aliquot,
    Antimicrobial,
    Assembly,
    AssemblyQC,
    Base,
    Isolate,
    TaxonomicAssignment,
)


SPECIAL_COLLECTIONS = ["Bacteremia", "Surveillance", None]
ST_SCHEMA = ["Pasteur", "Achtman", None]
RESISTANCE_PRODUCTS = [
    "Beta-lactamase",
    "Aminoglycoside-modifying enzyme",
    "Efflux pump",
    "Target protection",
    "Ribosomal methyltransferase",
]


def random_date_within(days: int) -> date:
    """Return a date within the last ``days`` days."""

    offset = random.randint(0, days)
    return date.today() - timedelta(days=offset)


def reset_database(engine) -> None:
    """Drop and recreate all MARC tables."""

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed_isolate(index: int) -> Isolate:
    sample_id = f"ISO-{index:04d}"
    subject_id = 10_000 + index
    specimen_id = 500_000 + index
    suspected_organism = random.choice(
        ["E. coli", "Klebsiella pneumoniae", "Staphylococcus aureus", "unknown"]
    )
    special_collection = random.choice(SPECIAL_COLLECTIONS)
    received_date = random_date_within(400)
    cryobanking_date = received_date + timedelta(days=random.randint(0, 14))
    return Isolate(
        sample_id=sample_id,
        subject_id=subject_id,
        specimen_id=specimen_id,
        suspected_organism=suspected_organism,
        special_collection=special_collection,
        received_date=received_date,
        cryobanking_date=cryobanking_date,
    )


def seed_assembly(isolate: Isolate, assembly_index: int) -> Assembly:
    run_number = f"RUN-{assembly_index:03d}"
    return Assembly(
        isolate_id=isolate.sample_id,
        metagenomic_sample_id=f"MG-{assembly_index:04d}",
        metagenomic_run_id=f"MGR-{assembly_index:04d}",
        nanopore_path=f"/data/nanopore/{run_number}",
        run_number=run_number,
        sunbeam_version="3.0.0",
        sbx_sga_version="1.2.0",
        sunbeam_output_path=f"/data/sunbeam/{run_number}",
    )


def seed_assembly_qc(assembly: Assembly) -> AssemblyQC:
    genome_size = random.randint(4_000_000, 6_000_000)
    coverage = random.uniform(25, 120)
    return AssemblyQC(
        assembly=assembly,
        contig_count=random.randint(50, 250),
        genome_size=genome_size,
        n50=random.randint(20_000, 200_000),
        gc_content=round(random.uniform(0.35, 0.72), 3),
        cds=random.randint(4_000, 7_000),
        completeness=round(random.uniform(80.0, 100.0), 2),
        contamination=round(random.uniform(0.0, 5.0), 2),
        min_contig_coverage=round(coverage * 0.75, 2),
        avg_contig_coverage=round(coverage, 2),
        max_contig_coverage=round(coverage * 1.2, 2),
    )


def seed_taxonomic_assignment(assembly: Assembly) -> TaxonomicAssignment:
    taxonomy = random.choice(
        [
            "Escherichia coli",
            "Klebsiella pneumoniae",
            "Staphylococcus aureus",
            "Pseudomonas aeruginosa",
        ]
    )
    return TaxonomicAssignment(
        assembly=assembly,
        taxonomic_classification=taxonomy,
        taxonomic_abundance=round(random.uniform(80.0, 99.9), 2),
        mash_contamination=round(random.uniform(0.0, 3.5), 2),
        mash_contaminated_spp=random.choice(["None", "Low-level contamination"]),
        st=str(random.randint(1, 2000)),
        st_schema=random.choice(ST_SCHEMA),
        allele_assignment=f"{taxonomy} allele set",
    )


def seed_antimicrobials(assembly: Assembly, count: int = 2) -> list[Antimicrobial]:
    records: list[Antimicrobial] = []
    for idx in range(count):
        records.append(
            Antimicrobial(
                assembly=assembly,
                contig_id=f"contig_{idx}",
                gene_symbol=f"gene_{idx}",
                gene_name=f"Gene Name {idx}",
                accession=f"ACC{idx:05d}",
                element_type="plasmid" if idx % 2 == 0 else "chromosome",
                resistance_product=random.choice(RESISTANCE_PRODUCTS),
            )
        )
    return records


def seed_aliquots(isolate: Isolate, aliquots_per_isolate: int) -> list[Aliquot]:
    aliquots: list[Aliquot] = []
    for tube_idx in range(aliquots_per_isolate):
        aliquots.append(
            Aliquot(
                isolate_id=isolate.sample_id,
                tube_barcode=f"TB-{isolate.sample_id}-{tube_idx:03d}",
                box_name=f"BOX-{tube_idx % 10:02d}",
            )
        )
    return aliquots


def populate_database(
    session: Session, isolates: int, aliquots_per_isolate: int
) -> None:
    for isolate_index in range(isolates):
        isolate = seed_isolate(isolate_index)
        session.add(isolate)

        aliquots = seed_aliquots(isolate, aliquots_per_isolate)
        session.add_all(aliquots)

        assembly = seed_assembly(isolate, isolate_index)
        session.add(assembly)

        qc = seed_assembly_qc(assembly)
        tax = seed_taxonomic_assignment(assembly)
        antimicrobials = seed_antimicrobials(assembly, count=3)

        session.add(qc)
        session.add(tax)
        session.add_all(antimicrobials)

    session.commit()


def write_last_sync(path: Path) -> None:
    path.write_text(datetime.utcnow().isoformat())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "db_file",
        type=Path,
        help="Path to the SQLite database file to create (will be overwritten).",
    )
    parser.add_argument(
        "--isolates",
        type=int,
        default=75,
        help="Number of isolates to create (default: 75).",
    )
    parser.add_argument(
        "--aliquots-per-isolate",
        type=int,
        default=4,
        help="Number of aliquots per isolate (default: 4, yielding 300 aliquots).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic data generation.",
    )
    parser.add_argument(
        "--last-sync-file",
        type=Path,
        help=(
            "Optional path to write a MARC_DB_LAST_SYNC timestamp. "
            "The parent directory will be created if needed."
        ),
    )

    args = parser.parse_args()

    random.seed(args.seed)

    db_file = args.db_file.resolve()
    if db_file.exists():
        db_file.unlink()
    db_file.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_file}", future=True)
    reset_database(engine)

    with Session(engine) as session:
        populate_database(
            session,
            isolates=args.isolates,
            aliquots_per_isolate=args.aliquots_per_isolate,
        )

    if args.last_sync_file:
        args.last_sync_file.parent.mkdir(parents=True, exist_ok=True)
        write_last_sync(args.last_sync_file)

    print(f"Created synthetic database at {db_file}")
    if args.last_sync_file:
        print(f"Wrote MARC_DB_LAST_SYNC timestamp to {args.last_sync_file}")


if __name__ == "__main__":
    main()
