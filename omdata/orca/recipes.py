from __future__ import annotations

import os

import psutil
from quacc.recipes.orca.core import run_and_summarize, run_and_summarize_opt

from omdata.orca.calc import (
    OPT_PARAMETERS,
    ORCA_BASIS,
    ORCA_BLOCKS,
    ORCA_FUNCTIONAL,
    ORCA_SIMPLE_INPUT,
)


def single_point_calculation(
    atoms,
    charge,
    spin_multiplicity,
    xc=ORCA_FUNCTIONAL,
    basis=ORCA_BASIS,
    orcasimpleinput=None,
    orcablocks=None,
    nprocs=12,
    outputdir=os.getcwd(),
    **calc_kwargs,
):
    """
    Wrapper around QUACC's static job to standardize single-point calculations.
    See github.com/Quantum-Accelerators/quacc/blob/main/src/quacc/recipes/orca/core.py#L22
    for more details.

    Arguments
    ---------

    atoms: Atoms
        Atoms object
    charge: int
        Charge of system
    spin_multiplicity: int
        Multiplicity of the system
    xc: str
        Exchange-correlaction functional
    basis: str
        Basis set
    orcasimpleinput: list
        List of `orcasimpleinput` settings for the calculator
    orcablocks: list
        List of `orcablocks` swaps for the calculator
    nprocs: int
        Number of processes to parallelize across
    outputdir: str
        Directory to move results to upon completion
    calc kwargs: dict
        Additional kwargs for the custom Orca calculator
    """
    from quacc import SETTINGS

    SETTINGS.RESULTS_DIR = outputdir

    if orcasimpleinput is None:
        orcasimpleinput = ORCA_SIMPLE_INPUT.copy()
    if orcablocks is None:
        orcablocks = ORCA_BLOCKS.copy()

    nprocs = psutil.cpu_count(logical=False) if nprocs == "max" else nprocs
    default_inputs = [xc, basis, "engrad", "normalprint"]
    default_blocks = [f"%pal nprocs {nprocs} end"]

    doc = run_and_summarize(
        atoms,
        charge=charge,
        spin_multiplicity=spin_multiplicity,
        default_inputs=default_inputs,
        default_blocks=default_blocks,
        input_swaps=orcasimpleinput,
        block_swaps=orcablocks,
        **calc_kwargs,
    )

    return doc


def ase_relaxation(
    atoms,
    charge,
    spin_multiplicity,
    xc=ORCA_FUNCTIONAL,
    basis=ORCA_BASIS,
    orcasimpleinput=None,
    orcablocks=None,
    nprocs=12,
    opt_params=None,
    outputdir=os.getcwd(),
    **calc_kwargs,
):
    """
    Wrapper around QUACC's ase_relax_job to standardize geometry optimizations.
    See github.com/Quantum-Accelerators/quacc/blob/main/src/quacc/recipes/orca/core.py#L22
    for more details.

    Arguments
    ---------

    atoms: Atoms
        Atoms object
    charge: int
        Charge of system
    spin_multiplicity: int
        Multiplicity of the system
    xc: str
        Exchange-correlaction functional
    basis: str
        Basis set
    orcasimpleinput: list
        List of `orcasimpleinput` settings for the calculator
    orcablocks: list
        List of `orcablocks` swaps for the calculator
    nprocs: int
        Number of processes to parallelize across
    opt_params: dict
        Dictionary of optimizer parameters
    outputdir: str
        Directory to move results to upon completion
    calc kwargs: dict
        Additional kwargs for the custom Orca calculator
    """
    from quacc import SETTINGS

    SETTINGS.RESULTS_DIR = outputdir

    if orcasimpleinput is None:
        orcasimpleinput = ORCA_SIMPLE_INPUT.copy()
    if orcablocks is None:
        orcablocks = ORCA_BLOCKS.copy()
    if opt_params is None:
        opt_params = OPT_PARAMETERS.copy()

    nprocs = psutil.cpu_count(logical=False) if nprocs == "max" else nprocs
    default_inputs = [xc, basis, "engrad", "normalprint"]
    default_blocks = [f"%pal nprocs {nprocs} end"]

    if "feje_project" in calc_kwargs:
        import quacc.recipes.orca._base
        from fair_chemistry_workflows.quacc.internal.calculators.orca.feje_orca import (
            FejeORCA,
        )

        # monkey patch Orca calculator
        quacc.recipes.orca._base.ORCA = FejeORCA

    doc = run_and_summarize_opt(
        atoms,
        charge=charge,
        spin_multiplicity=spin_multiplicity,
        default_inputs=default_inputs,
        default_blocks=default_blocks,
        input_swaps=orcasimpleinput,
        block_swaps=orcablocks,
        opt_params=opt_params,
        **calc_kwargs,
    )

    return doc
