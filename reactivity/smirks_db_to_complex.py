from typing import List, Tuple

from more_itertools import collapse
from rdkit import Chem
from rdkit.Chem import AllChem
from schrodinger.application.jaguar.autots_input import AutoTSInput
from schrodinger.application.jaguar.file_logger import FileLogger
from schrodinger.application.jaguar.packages.autots_modules.active_bonds import (
    mark_active_bonds,
)
from schrodinger.application.jaguar.packages.autots_modules.complex_formation import (
    _add_atom_transfer_dummies,
    _remove_atom_transfer_dummies,
    minimize_path_distance,
    reaction_center,
    translate_close,
)
from schrodinger.application.jaguar.packages.autots_modules.renumber import (
    build_reaction_complex,
)
from schrodinger.application.jaguar.packages.reaction_mapping import (
    build_reaction_complex as get_renumbered_complex,
)
from schrodinger.application.jaguar.packages.reaction_mapping import flatten_st_list
from schrodinger.rdkit import rdkit_adapter
from schrodinger.structure import Structure, StructureWriter

"""
Convert Reaction SMIRKS (from RMechDB/PMechDB) to 3D fully mapped complexes.
"""


class local_rinp(AutoTSInput):
    """
    Need a patched version that I can populated programatically easily
    """

    def __init__(self, reactants, products):
        super().__init__()
        self.reactants = reactants
        self.products = products

    def getReactants(self):
        return self.reactants

    def getProducts(self):
        return self.products


def build_complexes(
    reactants: List[Structure], products: List[Structure]
) -> Tuple[Structure, Structure]:
    """
    Build the reaction complexes.

    This tries to use the built-in Schrodinger tools but if you don't
    have full licenses (i.e. the academic version), you might not be
    able to use it. Hence, I've also written a minimal version that will
    at least work if not as well as the Schrodinger one.
    """
    rinp = local_rinp(reactants, products)
    rinp.values.debug = False
    reactants, products = mark_active_bonds(
        reactants, products, max_n_active_bonds=10, water_wire=False
    )

    try:
        with FileLogger("logger", True):
            reactant_complex, product_complex = build_reaction_complex(
                reactants, products, rinp
            )
    except Exception as e:
        print(e)
        print(
            "getting renumbered complexes but can't do assembly. This is probably a license issue"
        )
        reactants = flatten_st_list(reactants)
        products = flatten_st_list(products)
        reactant_complex, product_complex = get_renumbered_complex(reactants, products)
        reactant_complex, product_complex = minimal_form_reaction_complex(
            reactant_complex, product_complex, rinp
        )

    return reactant_complex, product_complex


def minimal_form_reaction_complex(
    reactant: Structure, product: Structure, rinp: local_rinp
) -> Tuple[Structure, Structure]:
    reactant_out = reactant.copy()
    product_out = product.copy()

    rxn_center = reaction_center(reactant, product)

    # add dummy atoms to handle single atom transfers
    added_dummies = _add_atom_transfer_dummies(reactant_out, product_out)

    reactant_out, product_out = minimize_path_distance(
        reactant_out,
        product_out,
        indep_only=True,
        check_stab=rinp.values.check_alignment_stability,
    )

    translate_close(
        reactant_out, rxn_center=rxn_center, vdw_scale=rinp.values.vdw_scale
    )
    translate_close(product_out, rxn_center=rxn_center, vdw_scale=rinp.values.vdw_scale)
    # remove dummy atoms before returning
    _remove_atom_transfer_dummies(reactant_out)
    _remove_atom_transfer_dummies(product_out)

    return reactant_out, product_out


# nh3I = Chem.MolFromSmiles('[NH3+]I.[Cl-]')
# nh3 = Chem.MolFromSmiles('N')
# I = Chem.MolFromSmiles('ICl')
# nh3I = rdkit_adapter.from_rdkit(nh3I)
# nh3 = rdkit_adapter.from_rdkit(nh3)
# I = rdkit_adapter.from_rdkit(I)
# rxn_list = {'name':([nh3I],[nh3,I])}

rxn_smirks = "[Li:11][CH2:10]CCC[CH:20]=[CH:21][C:22](=[O:23])OC(C)(C)C.CCCCI>>[Li+:11].CCCCI.CC(C)(C)O[C:22](=[CH:21][CH:20]1[CH2:10]CCC1)[O-:23] 10"
rxn = AllChem.ReactionFromSmarts(rxn_smirks)
# Add 3D to RDKit
r_mols = [Chem.AddHs(mol) for mol in rxn.GetReactants()]
p_mols = [Chem.AddHs(mol) for mol in rxn.GetProducts()]
for mol in collapse((r_mols, p_mols)):
    AllChem.EmbedMolecule(mol)

reactants = [rdkit_adapter.from_rdkit(mol) for mol in r_mols]
products = [rdkit_adapter.from_rdkit(mol) for mol in p_mols]
rxn_st = []

# *MechDBs sometimes include molecules with no mapped atoms which
# seem to be spectators. We exclude these molecules from the reaction
# complexes
for st_list in (reactants, products):
    rxn_st.append(
        [
            st
            for st in st_list
            if any("i_rdkit_molAtomMapNumber" in at.property for at in st.atom)
        ]
    )

rxn_list = {"name": rxn_st}


for name, rxn in rxn_list.items():
    try:
        for st in collapse(rxn):
            st.generate3dConformation(require_stereo=False)
    except Exception:
        print('SDGR graph to 3D generation failed. Probably no Canvas license. Proceeding with RDKit 3D coords')
    try:
        r, p = build_complexes(*rxn)
    except Exception as e:
        print(e)
        continue
    else:
        # Stick the total charge in the comment line of the .xyz
        r.title = f"charge={r.formal_charge}"
        p.title = f"charge={p.formal_charge}"
        with StructureWriter(f"{name}.xyz") as writer:
            writer.extend([r, p])
