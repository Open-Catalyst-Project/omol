from typing import List
import logging

logging.basicConfig(level=logging.INFO)
import random
import os
from tqdm import tqdm
import json
import argparse

from schrodinger.structure import StructureReader
from schrodinger.structutils import analyze
from solvation_shell_utils import (
    expand_shell,
    renumber_molecules_to_match,
    filter_by_rmsd,
)
from schrodinger.comparison import are_conformers
from schrodinger.application.jaguar.utils import group_with_comparison
from schrodinger.structutils import rmsd


def extract_solvation_shells(
    input_dir: str,
    save_dir: str,
    system_name: str,
    radii: List[float],
    top_n: int,
):
    """
    Given a MD trajectory in a PDB file, perform a solvation analysis
    on the specified solute to extract the first solvation shell.

    Args:
        input_dir: Path to 1) the PDB file containing the MD trajectory and 2) the LAMMPS file containing the initial structure (used to extract partial charges).
        save_dir: Directory in which to save extracted solvation shells.
        system_name: Name of the system - used for naming the save directory.
        radii: List of solvation shell radii to extract.
        top_n: Number of snapshots to extract per topology.
    """

    # Read a structure and metadata file
    # TODO: add charges
    logging.info("Reading structure and metadata files")

    # Read metadata
    with open(os.path.join(input_dir, "metadata_system.json")) as f:
        metadata = json.load(f)

    residue_to_species_and_type_mapping = {
        k: (v1, v2)
        for k, v1, v2 in zip(
            metadata["residue"], metadata["species"], metadata["solute_or_solvent"]
        )
    }

    solute_resnames = [
        k for k, v in residue_to_species_and_type_mapping.items() if v[1] == "solute"
    ]
    solvent_resnames = [
        k for k, v in residue_to_species_and_type_mapping.items() if v[1] == "solvent"
    ]

    # Read a structure
    structures = StructureReader(os.path.join(input_dir, "system_output.pdb"))

    # For each solute: extract shells around the solute of some heuristic radii and bin by composition/graph hash
    # Choose the N most diverse in each bin
    # Repeat this for each solvent
    logging.info("Extracting solvation shells from MD trajectory")
    expanded_shells = []
    for i, st in tqdm(enumerate(structures)):  # loop over timesteps
        if i > 10:
            break

        for residue, (species, _type) in residue_to_species_and_type_mapping.items():
            # TODO: instead loop over all solute residues
            if _type == "solute" and species == "Li+":
                # extract all atoms in this solute
                solute_molecules = [
                    res for res in st.residue if res.pdbres == f"{residue} "
                ]
                central_solute_nums = [mol.molecule_number for mol in solute_molecules]
                # Extract solvation shells containing entire residues within 3 angstroms of each molecule
                # if only part of a residue is within the radius, include the whole thing
                shells = [
                    set(
                        analyze.evaluate_asl(
                            st, f"fillres within {radii[0]} mol {mol_num}"
                        )
                    )
                    for mol_num in central_solute_nums
                ]

                # Now expand the shells
                for shell, central_solute in zip(shells, central_solute_nums):
                    expanded_shell = expand_shell(
                        st,
                        shell,
                        central_solute,
                        radii[0],
                        solute_resnames,
                        max_shell_size=200,
                    )
                    expanded_shells.append(expanded_shell)

    # Now compare the expanded shells and group them by similarity
    # we will get lists of lists of shells where each list of structures are conformers of each other
    logging.info("Grouping solvation shells into conformers")
    grouped_shells = group_with_comparison(expanded_shells, are_conformers)

    # Now ensure that topologically related atoms are equivalently numbered (up to molecular symmetry)
    grouped_shells = [renumber_molecules_to_match(items) for items in grouped_shells]

    # Now extract the top N most diverse shells from each group
    logging.info(f"Extracting top {top_n} most diverse shells from each group")
    final_shells = []
    # example grouping - set of structures
    for shell_group in tqdm(grouped_shells):
        filtered_shells = filter_by_rmsd(shell_group, n=top_n)
        final_shells.extend(filtered_shells)

    # Save the final shells
    logging.info("Saving final solvation shells")
    save_path = os.path.join(save_dir, system_name)
    os.makedirs(save_path, exist_ok=True)
    for i, st in enumerate(final_shells):
        st.write(os.path.join(save_path, f"shell_{i}.xyz"))


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    random.seed(10)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir",
        type=str,
        help="Path containing PDB trajectory and LAMMPS data files",
    )
    parser.add_argument("--save_dir", type=str, help="Path to save xyz files")
    parser.add_argument(
        "--system_name", type=str, help="Name of system used for directory naming"
    )

    parser.add_argument(
        "--radii",
        type=list,
        default=[3, 6],
        help="List of solvation shell radii to extract",
    )

    parser.add_argument(
        "--top_n",
        type=int,
        default=20,
        help="Number of most diverse shells to extract per topology",
    )

    args = parser.parse_args()

    extract_solvation_shells(
        args.input_dir,
        args.save_dir,
        args.system_name,
        args.radii,
        args.top_n,
    )
