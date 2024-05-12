"""lammps2omm.py 
Author: Muhammad R. Hasyim

Module to convert LAMMPS force field and DATA files to OpenMM
XML force field file and PDB file. The script is only tested with 
The forcefield files contained in './ff' so far and the following types 
    1. pair_coeff (LJ)
    2. bond_coeff
    3. angle_coeff
    4. dihedral_coeff
    5. improper_coeff

The script is heavily modified from:
'https://github.com/mrat1618/ff-conversion-openmm/lammps2omm.py'
'https://github.com/mrat1618/ff-conversion-openmm/main.lammps.py'
"""

import re
import math
import numpy as np
from itertools import combinations

## Data from LAMMPS DATA file

lmp_id = [] 
lmp_type = [] 
lmp_mass = [] 

lmp_bondtype = [] 
lmp_bond_ids = [] 

lmp_angletype = [] 
lmp_angle_ids = []

lmp_dihedraltype = []
lmp_dihedral_ids = []

lmp_impropertype = []
improper_atomids_list = []

lmp_alltypes = []
lmp_allids = []
lmp_allels = []
lmp_allcharges = []

## Force field styles from *.in.init file 
bondstyles = []
anglestyles = []
dihedralstyles = []
improperstyles = []
pairstyles = []

## Data from PDB file generated by Moltemplate
pdb_ids_mol = []
pdb_names = []
pdb_resname_mol = []
pdb_resnames = []


def _get_types(line):
    """ Obtain atom ids, mass, and types from LAMMPS DATA file
        
        Args:
            line (string): A string obtained from a line in LAMMPS DATA file
    """
    
    global lmp_id
    global lmp_mass
    global lmp_type

    line = line.split()
    lmp_id.append(int(line[0]))
    lmp_mass.append(float(line[1]))
    lmp_type.append(line[3].lower())

def _get_atoms(line):
    """ Obtain atom types, ids, names of elements, and charges from LAMMPS DATA file
        This list has the length of number of atoms. 

        Args:
            line (string): A string obtained from a line in LAMMPS DATA file
    """
    
    global lmp_alltypes
    global lmp_allids
    global lmp_allels
    global lmp_allcharges

    line = line.split()
    lmp_alltypes.append(lmp_type[int(line[2])-1])
    lmp_allids.append(int(line[2]))#lmp_type[int(line[2])-1])
    elname = extract_and_capitalize(lmp_type[int(line[2])-1])
    lmp_allels.append(elname)
    lmp_allcharges.append(float(line[3]))
    
def _get_bondtypes(line):
    """ Obtain bond type and ids from LAMMPS data file
        
        Args:
            line (string): A string obtained from a line in LAMMPS DATA file
    """
    
    global lmp_bondtype
    global lmp_bond_ids

    line = line.split()
    lmp_bondtype.append(int(line[1]))
    lmp_bond_ids.append((int(line[2]),int(line[3])))

def _get_angletypes(line):
    """ Obtain angle type and ids from LAMMPS data file
        
        Args:
            line (string): A string obtained from a line in LAMMPS DATA file
    """
    
    global lmp_angletype
    global lmp_angle_ids

    line = line.split()
    lmp_angletype.append(int(line[1]))
    lmp_angle_ids.append((int(line[2]),int(line[3]),int(line[4])))

def _get_dihedraltypes(line):
    """ Obtain dihedral type and ids from LAMMPS data file
        
        Args:
            line (string): A string obtained from a line in LAMMPS DATA file
    """
    
    global lmp_dihedraltype
    global lmp_dihedral_ids

    line = line.split()
    lmp_dihedraltype.append(int(line[1]))
    lmp_dihedral_ids.append((int(line[2]),int(line[3]),int(line[4]),int(line[5])))

def _get_impropertypes(line):
    """ Obtain improper type and ids from LAMMPS data file
        
        Args:
            line (string): A string obtained from a line in LAMMPS DATA file
    """
    
    global lmp_impropertype
    global lmp_improper_ids
    
    line = line.split()
    lmp_impropertype.append(int(line[1]))
    improper_atomids_list.append((int(line[2]),int(line[3]),int(line[4]),int(line[5])))

## Dictionary of atomic masses and element names
## For numbering 
atomic_masses_rounded = {
    1: 'H', 4: 'He', 7: 'Li', 9: 'Be', 11: 'B',
    12: 'C', 14: 'N', 16: 'O', 19: 'F', 20: 'Ne',
    23: 'Na', 24: 'Mg', 27: 'Al', 28: 'Si', 31: 'P',
    32: 'S', 35: 'Cl', 40: 'Ar', 39: 'K', 40: 'Ca',
    45: 'Sc', 48: 'Ti', 51: 'V', 52: 'Cr', 55: 'Mn',
    56: 'Fe', 59: 'Co', 59: 'Ni', 63: 'Cu', 65: 'Zn',
    70: 'Ga', 73: 'Ge', 75: 'As', 79: 'Se', 80: 'Br',
    84: 'Kr', 85: 'Rb', 88: 'Sr', 89: 'Y', 91: 'Zr',
    93: 'Nb', 96: 'Mo', 98: 'Tc', 101: 'Ru', 103: 'Rh',
    106: 'Pd', 108: 'Ag', 112: 'Cd', 115: 'In', 119: 'Sn',
    122: 'Sb', 128: 'Te', 127: 'I', 131: 'Xe', 133: 'Cs',
    137: 'Ba', 139: 'La', 140: 'Ce', 141: 'Pr', 144: 'Nd',
    145: 'Pm', 150: 'Sm', 152: 'Eu', 157: 'Gd', 159: 'Tb',
    163: 'Dy', 165: 'Ho', 167: 'Er', 169: 'Tm', 173: 'Yb',
    175: 'Lu', 178: 'Hf', 181: 'Ta', 184: 'W', 186: 'Re',
    190: 'Os', 192: 'Ir', 195: 'Pt', 197: 'Au', 201: 'Hg',
    204: 'Tl', 207: 'Pb', 209: 'Bi', 209: 'Po', 210: 'At', 222: 'Rn',
    223: 'Fr', 226: 'Ra', 227: 'Ac', 232: 'Th', 231: 'Pa', 238: 'U',
    237: 'Np', 244: 'Pu', 243: 'Am', 247: 'Cm', 247: 'Bk', 251: 'Cf',
    252: 'Es', 257: 'Fm', 258: 'Md', 259: 'No', 262: 'Lr', 267: 'Rf',
    270: 'Db', 271: 'Sg', 270: 'Bh', 269: 'Hs', 278: 'Mt',
}

#Conversion units
radian2degree = 57.2957795130  # 1 rad  = 57.2957795130 degree
degree2radian = 0.0174533      # Reciprocal of degree2radian
kcal2kj       = 4.184          # 1 kcal = 4.184 kj
ang2nm        = 0.1            # 1 Angstrom = 0.1 nanometers

# grey colour bash text variable. marks unconverted lines in less pronounced light grey colour.
CGREY = '\33[90m'
CYLW = '\33[33m'
CEND = '\33[0m'

"""Helper function to extract molecule name from the filename""" 
extract_and_capitalize = lambda text: re.match(r'([A-Za-z]+)', text).group(1).capitalize() if re.match(r'([A-Za-z]+)', text) else None

def write_pdbfile(u,filename):
    """Writes the final PDB file used for initializing OpenMM simulation

    Args:
        u (MDAnalysis.Universe): A Universe object loaded from LAMMPS DATA file
        filename (string): Name of PDB file pre-appended to the formatted name. 
    """
    
    #First, write the PDB file from Universe object
    fname = filename+'_init.pdb'
    ag = u.atoms
    ag.write(fname)
    
    #Make sure to generate CONECT information!
    pdbconect = ""
    for i, bond in enumerate(lmp_bond_ids):
        pdbconect += f"CONECT {bond[0]:>{4}} {bond[1]:>{4}} \n"
    pdbconect += "END \n"

    #Load the written PDB file again and delete the 'END' line 
    with open(fname,'r') as file:
        lines = file.readlines()
    if lines:
        lines.pop()
    with open(fname, 'w') as file:
        file.writelines(lines)

    # Now, append the PDB CONECT information
    with open(fname, 'a') as file:
        file.write(pdbconect)

#(4) Read the Force Field file
def write_forcefield(u,filename):
    """Writes the final XML file used for performing an OpenMM simulation

    Args:
        u (MDAnalysis.Universe): A Universe object loaded from LAMMPS DATA file
        filename (string): Name of XML file pre-appended to the formatted name. 
    """
    
    global bondstyles
    global anglestyles
    global dihedralstyles
    global improperstyles
    global pairstyles

    
    # Read the *.in.init file to check what force field styles are present
    fname = filename+'.in.init'
    with open(fname,'r') as params:
        for line in params:
            cleaned_line = line.strip()
            if len(cleaned_line) >= 1 and cleaned_line.split()[0] == "bond_style":
                bondstyles = cleaned_line.split()[1:]
            if len(cleaned_line) >= 1 and cleaned_line.split()[0] == "angle_style":
                anglestyles = cleaned_line.split()[1:]
            if len(cleaned_line) >= 1 and cleaned_line.split()[0] == "dihedral_style":
                dihedralstyles = cleaned_line.split()[1:]
            if len(cleaned_line) >= 1 and cleaned_line.split()[0] == "improper_style":
                improperstyles = cleaned_line.split()[1:]
            if len(cleaned_line) >= 1 and cleaned_line.split()[0] == "pair_style":
                pairstyles = cleaned_line.split()[1:]

    # Read the *.in.settings to load the force field parameters
    # Lists to store the force force field parameters from LAMMPS
    bond_out = []
    angle_out = []
    torsion_out = []
    nonbond_out = []
    
    # Load the *.in.settings file
    fname = filename+'.in.settings'
    with open(fname, 'r') as params:
        # Grab all force field parameters
        for line in params:
            cleaned_line = line.strip()
            if len(cleaned_line) >= 1 and cleaned_line.split()[0] == "bond_coeff":
                bond_out.append(_bond(cleaned_line))
            elif len(cleaned_line) >= 1 and cleaned_line.split()[0] == "angle_coeff":
                angle_out.append(_angle(cleaned_line))
            elif len(cleaned_line) >= 1 and cleaned_line.split()[0] == "dihedral_coeff":
                torsion_out.append(_dihedral(cleaned_line))
            elif len(cleaned_line) >= 1 and cleaned_line.split()[0] == "improper_coeff":
                torsion_out.append(_improper(cleaned_line))
            elif len(cleaned_line) >= 1 and cleaned_line.split()[0] == "pair_coeff":
                nonbond_out.append(_nonbonding(cleaned_line))
            else:
                print(CGREY+cleaned_line+CEND)

    # Start writing the XML file
    omm_ff = filename+'.xml'
    with open(omm_ff,"w") as ff:
        ff.write("<ForceField>\n")
        
        # Write the Atom Types
        ff.write("<AtomTypes>\n")
        for i, atomtype in enumerate(lmp_type):
            elname = atomic_masses_rounded.get(int(np.round(lmp_mass[i])),'UNK')
            ff.write(f' <Type name="{atomtype}" class="{elname}" element="{elname}" mass="{lmp_mass[i]}"/> \n')
        ff.write("</AtomTypes>\n")
        
        # Generate the residue template. A species is its own residue
        residue_template = write_restemplate(u)
        ff.write(residue_template)
        
        #Next, we write the force field parameters
        #(1) Bonded Interactions
        harmonic_bonds = list(filter(lambda x: x[0] == 'harmonic', bond_out))
        ff.write('<HarmonicBondForce>\n')
        for line in harmonic_bonds:
            ff.write(line[1]+"\n")
        ff.write('</HarmonicBondForce>\n')
        
        #(2) Angle Interactions
        harmonic_angles = list(filter(lambda x: x[0] == 'harmonic', angle_out))
        ff.write('<HarmonicAngleForce>\n')
        for line in harmonic_angles:
            ff.write(line[1]+"\n")
        ff.write('</HarmonicAngleForce>\n')
        
        #(3) Improper Interactions
        impropers = list(filter(lambda x: x[0] == 'improper', torsion_out))
        cvff_impropers = list(filter(lambda x: x[1] == 'cvff', impropers))
        ff.write('<PeriodicTorsionForce>\n')
        for line in cvff_impropers:
            ff.write(line[2]+"\n")
        ff.write('</PeriodicTorsionForce>\n')
        
        #(4) Dihedral Interactions
        #With the current force field files, dihedral is either opls or improper
        dihedrals = list(filter(lambda x: x[0] == 'dihedral', torsion_out))
        opls_dihedrals = list(filter(lambda x: x[1] == 'opls', dihedrals))
        if opls_dihedrals:
            ff.write('<PeriodicTorsionForce>\n')
            for line in opls_dihedrals:
                ff.write(line[2]+"\n")
            ff.write('</PeriodicTorsionForce>\n')
        
        fourier_dihedrals = list(filter(lambda x: x[1] == 'fourier', dihedrals))
        if fourier_dihedrals:
            ff.write('<CustomTorsionForce energy="k1*(1+cos(n1*theta-d1))+k2*(1-cos(n2*theta-d2))+k3*(1+cos(n3*theta-d3))">\n')
            for i in range(1,4):
                ff.write(f"""<PerTorsionParameter name="k{i}"/>
<PerTorsionParameter name="n{i}"/>
<PerTorsionParameter name="d{i}"/>
""")
            for line in fourier_dihedrals:
                ff.write(line[2]+"\n")
            ff.write('</CustomTorsionForce>\n') 

        #(5) NonBonded Interaction
        ff.write('<NonbondedForce coulomb14scale="0.5" lj14scale="0.5">\n')
        for line in nonbond_out: 
            ff.write(line[0]+"\n")
        ff.write('</NonbondedForce>\n')
        
        ff.write("</ForceField>\n")
    ff.close()


def find_combination(numbers_list, target_tuple):
    """Helper function to check if a pair of numbers is present in all possible combinations of a list
    
        Args: 
        numbers_list (list): A list of all possbile numbers
        target_typle (tuple): A tuple of numbers to match with the combinations of numbers_list
    """
    for combo in combinations(numbers_list, 2):
        if sorted(combo) == sorted(target_tuple):
            return True
    return False

def write_restemplate(u):
    """Generates a residue template for the XML force field file
    
        Args: 
            u (MDAnalysis.Universe): A Universe object loaded from the LAMMPS DATA file
    """
    
    text = "<Residues>\n"
    resnames = list(set(pdb_resname_mol))
    for resname in resnames:
        text += f' <Residue name="{resname}">\n'
        bond_text = ""
        names = []
        types = []
        
        #Go through and write the bond information
        for i, bond in enumerate(lmp_bond_ids):
            if u.atoms[bond[0]-1].resname == resname and find_combination(pdb_ids_mol,bond):
                names.append(u.atoms[bond[0]-1].name)      
                names.append(u.atoms[bond[1]-1].name)      
                types.append(lmp_alltypes[bond[0]-1])
                types.append(lmp_alltypes[bond[1]-1])
                bond_text += f'  <Bond atomName1="{pdb_names[bond[0]-1]}" atomName2="{pdb_names[bond[1]-1]}" /> \n'
        #Write the atom names and types associated with the bond information
        if types and names:
            r, d = zip(*((r, types[i]) for i, r in enumerate(names) if r not in names[:i]))
            for i in range(len(r)):
                text += f'  <Atom name="{r[i]}" type="{d[i]}"/> \n'
            text += bond_text
        #If either no bonds are present, then we have a single atom, i.e., Na+ ion or Cl- ion.
        else:
            idx = pdb_resnames.index(resname)
            print(resname,pdb_names[idx],lmp_alltypes[idx])
            text += f'  <Atom name="{pdb_names[idx]}" type="{lmp_alltypes[idx]}"/> \n'
        text += ' </Residue>\n'
    text += "</Residues>\n"
    return text

def grab_pdbdata_attr(pdb_file):
    """Reads the data from PDB file and save to lists

        Args: 
            pdb_file (string): fname of the PDB file to load
    
        Here we make a rule. Each molecule is assigned as its own residue. 
        In the PDB file, every molecule has its unique chainID, e.g., A or B or C, etc.
        The residue name will be triple of the chain ID, e.g., A -> AAA, B -> BBB.
    """
    with open(pdb_file, 'r') as file:
        lines = file.readlines()
        chainID = []
        molID = []
        molid = 0
        
        for line in lines:
            lsplit = line.split()
            if lsplit[0] == 'ATOM' or lsplit[0] == 'HETATM':
                if lsplit[4] not in chainID:
                    chainID.append(lsplit[4])
                    molID.append(lsplit[5])
                    molid = 0
                if molID[-1] == lsplit[5]:
                    pdb_ids_mol.append(int(lsplit[1]))
                pdb_names.append(lsplit[2])
                pdb_resnames.append(lsplit[4]*3)
                if np.abs(molid-int(lsplit[5])) > 0:
                    pdb_resname_mol.append(lsplit[4]*3)
                    molid = int(lsplit[5])

def grab_lmpdata_attr(dname):
    """Reads the data from LAMMPS data file and save to lists

        Args: 
            dname (string): fname of the LAMMPS DATA file to load
    
        Here we make a rule. Each molecule is assigned as its own residue. 
        In the PDB file, every molecule has its unique chainID, e.g., A or B or C, etc.
        The residue name will be triple of the chain ID, e.g., A -> AAA, B -> BBB.
    """
    global lmp_id
    global lmp_mass
    global lmp_type

    namelist = ["Masses","Atoms","Bonds","Angles","Dihedrals","Impropers"]
    checks = [False]*len(namelist)
    with open(dname,"r") as params:
        for line in params:
            cleaned_line = line.strip()
            for name in namelist:
                if name in cleaned_line:
                    checks = [False]*len(namelist)
                    idx = namelist.index(name)
                    checks[idx] = True
            if checks[0] and len(cleaned_line.split()) == 4:
                _get_types(cleaned_line)
                sorted_indices = [index for index, _ in sorted(enumerate(lmp_id), key=lambda x: x[1])]
                lmp_id = np.array(lmp_id)[sorted_indices].tolist()
                lmp_mass = np.array(lmp_mass)[sorted_indices].tolist()
                lmp_type = np.array(lmp_type)[sorted_indices].tolist()
            if checks[1] and len(cleaned_line.split()) == 7:
                _get_atoms(cleaned_line)
            if checks[2] and len(cleaned_line.split()) == 4:
                _get_bondtypes(cleaned_line)
            if checks[3] and len(cleaned_line.split()) == 5:
                _get_angletypes(cleaned_line)
            if checks[4] and len(cleaned_line.split()) == 6:
                _get_dihedraltypes(cleaned_line)
            if checks[5] and len(cleaned_line.split()) == 6:
                _get_impropertypes(cleaned_line)

## TO-DO: Update the documentation stings

def _bond(line):
    """(list:str) -> str
    Parameters: list: processed line from lammps param file
    Return    : Force Constant (K) and min.dist (r)
        K: kcal/mol/(A**2)  ->  K/2: 2*kj/mol/nm**2 (scale factor 2)
        r: Ang                ->  nm
    ----
    bond_coeff  1  338.69999999999999        1.0910000000000000  # c3-hx
    0           1  2                         3                   4 5    
                ^  ^                         ^
                   K                         r
    """
    llist     = line.split()
    bond_type = int(llist[1])
    k         = float(llist[2])
    r         = float(llist[3])

    omm_k  = k*2*kcal2kj/(ang2nm*ang2nm)
    omm_r  = r*ang2nm
    
    idx = lmp_bondtype.index(bond_type)# = []
    aid, bid = lmp_bond_ids[idx]
    aid = lmp_alltypes[aid-1]
    bid = lmp_alltypes[bid-1]
    bond_style = bondstyles[0]
    omm_out = ' <Bond type1="{}" type2="{}" length="{}" k="{}"/>'.format(aid,bid,omm_r, omm_k)
    
    print(omm_out)
    return [bond_style,omm_out] #(omm_out)


def _angle(line):
    """(list:str) -> str
    Parameters: list: processed line from lammps param file
    Return    : Force Constant (K) and min.angle (a)
        K: kcal/mol/(rad**2)  ->  K/2: 2*kj/mol/(rad**2) (scale factor 2)
        a: degrees            ->  rad
    ----
    angle_coeff  1  46.200000000000010        110.10999693591019  # c3-n4-hn 
    0            1  2                         3                   4 5
                    ^                         ^              
                    K                         a    
    """
    llist  = line.split()
    angle_type = int(llist[1])
    k      = float(llist[2])
    a      = float(llist[3])
    
    idx = lmp_angletype.index(angle_type)# = []
    aid, bid, cid = lmp_angle_ids[idx]
    omm_t1 = lmp_alltypes[aid-1]
    omm_t2 = lmp_alltypes[bid-1]
    omm_t3 = lmp_alltypes[cid-1]

    omm_k  = 2*k*kcal2kj#/(degree2radian*degree2radian)#ang2rad**2)
    omm_a  = math.radians(a)

    angle_style = anglestyles[0]
    omm_out = ' <Angle type1="{}" type2="{}" type3="{}" angle="{}" k="{}"/>'.format(omm_t1, omm_t2, omm_t3, omm_a, omm_k)

    print(omm_out)
    return [angle_style,omm_out]


def _dihedral(line):
    """(list:str) -> str
    OPLS dihedral
    Parameters: list: processed line from lammps param file
    Return    : 
        K:kcal/mol                      ->  K: kj/mol
        periodicity(n): integer >= 0    ->  int
        d(phase offset): degrees        ->  rad
        weigh.fac: read more at https://lammps.sandia.gov/doc/dihedral_charmm.html
                   must kept 0 for AMBER type lj/cut

    ----
    dihedral_coeff  1  0.15559999999999999     3   0   0.00000000    # hx-c3-n4-hn
    0               1  2                       3   4   5             6 7
                       ^                       ^   ^   ^           
                       K                       n   d   weigh.fac
    """
    #We have a hybrid style
    shift = 0
    llist  = line.split()
    dihedral_type = int(llist[1])
    if len(dihedralstyles) > 1:
        shift = 1
        dihedral_style = llist[1+shift] 
    else:
        dihedral_style = dihedralstyles[0]
    
    idx = lmp_dihedraltype.index(dihedral_type)# = []
    aid, bid, cid, did = lmp_dihedral_ids[idx]
    omm_t4 = lmp_alltypes[aid-1]
    omm_t3 = lmp_alltypes[bid-1]
    omm_t2 = lmp_alltypes[cid-1]
    omm_t1 = lmp_alltypes[did-1]

    if dihedral_style == "opls":
        k1 = float(llist[2+shift])/2
        k2 = float(llist[3+shift])/2
        k3 = float(llist[4+shift])/2
        k4 = float(llist[5+shift])/2

        omm_k1  = k1 * kcal2kj
        omm_k2  = k2 * kcal2kj
        omm_k3  = k3 * kcal2kj
        omm_k4  = k4 * kcal2kj

        omm_out = ' <Proper type1="{}" type2="{}" type3="{}" type4="{}" k1="{}" k2="{}" k3="{}" k4="{}" periodicity1="1" periodicity2="2" periodicity3="3" periodicity4="4" phase1="0.00" phase2="3.141592653589793" phase3="0.00" phase4="3.141592653589793"/>'.format(omm_t1, omm_t2, omm_t3, omm_t4, omm_k1, omm_k2, omm_k3, omm_k4)

        print(omm_out)
        return ["dihedral",dihedral_style,omm_out]
    
    elif dihedral_style == "fourier":
        nterms = int(llist[2+shift])
        k = []
        n = []
        d = []
        omm_out = ' <Proper type1="{}" type2="{}" type3="{}" type4="{}" '.format(omm_t1, omm_t2, omm_t3, omm_t4)
        for i in range(nterms):
            omm_out += f' k{i+1}="{float(llist[3*i+3+shift])*kcal2kj}"'
            omm_out += f' n{i+1}="{float(llist[3*i+4+shift])}"'
            omm_out += f' d{i+1}="{float(llist[3*i+5+shift])}"'
        omm_out += '/>'
        
        print(omm_out)
        return ["dihedral",dihedral_style,omm_out]

def _improper(line):
    """(list:str) -> str
    OPLS improper
    Parameters: list: processed line from lammps param file
    Return    : 
        K:kcal/mol                      ->  K: kj/mol
        periodicity(n): integer >= 0    ->  int
        d(phase offset): degrees        ->  rad
        weigh.fac: read more at https://lammps.sandia.gov/doc/improper_charmm.html
                   must kept 0 for AMBER type lj/cut

    ----
    improper_coeff  1  0.15559999999999999     3   0   0.00000000    # hx-c3-n4-hn
    0               1  2                       3   4   5             6 7
                       ^                       ^   ^   ^           
                       K                       n   d   weigh.fac
    """
    llist  = line.split()
    improper_type = int(llist[1])
    k = float(llist[2])
    d = float(llist[3]) 
    if d < 0:#== 1.0:
        theta = np.pi#0.0
    else:
        theta = 0.0
    n = float(llist[4])

    idx = lmp_impropertype.index(improper_type)# = []
    aid, bid, cid, did = improper_atomids_list[idx]
    omm_t1 = lmp_alltypes[aid-1]
    omm_t2 = lmp_alltypes[bid-1]
    omm_t3 = lmp_alltypes[cid-1]
    omm_t4 = lmp_alltypes[did-1]
    
    omm_k  = k * kcal2kj
    omm_n  = n#k2 * kcal2kj
    omm_theta  = theta#$k3 * kcal2kj

    omm_out = ' <Improper type1="{}" type2="{}" type3="{}" type4="{}" periodicity1="{}" phase1="{}" k1="{}"/>'.format(omm_t1, omm_t2, omm_t3, omm_t4, int(omm_n),omm_theta,omm_k)

    #print(omm_out)
    improper_style = improperstyles[0]
    return ["improper",improper_style,omm_out]


def _nonbonding(line):#,fixedtypes):
    """(list:str) -> str
    Parameters: list: processed line from lammps param file
    Return    : Force Constant (K) and min.angle (a)
        epsilon: kcal/mol       ->  kj/mol
        sigma  : angstrom       ->  nm       
    ----
    pair_coeff   1 3   lj/charmm/coul/long   1.4000000000000000E-002   2.2645400000000002  # pb-hn
    0            1 2   3                     4                         5                   6 7
                                             ^                         ^
                                             epsilon                   sigma
    """  
    llist = line.split()

    atom_id1 = llist[1]
    omm_t1 = lmp_type[int(atom_id1)-1]
    
    atom_id2 = llist[2]
    omm_t2 = lmp_type[int(atom_id2)-1]
    
    epsilon    = float(llist[3]) 
    sigma      = float(llist[4]) 

    omm_sigma   = ang2nm * sigma
    omm_epsilon = kcal2kj * epsilon

    # only output LJ pairs with same atom type
    if atom_id1 == atom_id2:# and llist[3].startswith("lj"):
        idx = lmp_allids.index(int(atom_id1))
        omm_charge = lmp_allcharges[idx]# = []
        omm_out = ' <Atom type="{}" charge="{}" sigma="{}" epsilon="{}"/>'.format(omm_t2, omm_charge, omm_sigma, omm_epsilon)
        print(omm_out)
    else:
        print(CGREY + line.strip() + CEND)
        omm_out=""
    return [omm_out]
