import os
import lzma
import requests
import pandas as pd
from conversion import ChemblUniprotConverter, process_in_parallel

# Define the URLs and the output directory
molecule_url = "https://zenodo.org/records/7019874/files/05.5++_combined_set_without_stereochemistry.tsv.xz"
protein_url = "https://zenodo.org/records/7019874/files/05.5_combined_set_protein_targets.tsv.xz"
output_directory = "./data/papyrus/"

def download_and_decompress(url, output_dir):
    # Get the filename from the URL
    filename = url.split('/')[-1]
    compressed_file_path = os.path.join(output_dir, filename)
    decompressed_file_path = os.path.join(output_dir, filename.replace('.xz', ''))

    # Download the file
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Check if the request was successful
    with open(compressed_file_path, 'wb') as compressed_file:
        for chunk in response.iter_content(chunk_size=8192):
            compressed_file.write(chunk)

    # Decompress the file
    with lzma.open(compressed_file_path, 'rb') as compressed_file:
        with open(decompressed_file_path, 'wb') as decompressed_file:
            decompressed_file.write(compressed_file.read())

    # Optionally remove the compressed file
    os.remove(compressed_file_path)

    return decompressed_file_path

def prepare_papyrus(molecule_url, protein_url, output_directory, pchembl_threshold=None, prot_len=None):
    # Create the output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)

    # Download and decompress the files
    molecule_file = download_and_decompress(molecule_url, output_directory)
    protein_file = download_and_decompress(protein_url, output_directory)

    print(f"Downloaded and decompressed molecule data to: {molecule_file}")
    print(f"Downloaded and decompressed protein data to: {protein_file}")
    
    mol_data = pd.read_csv(molecule_file, sep='\t')
    prot_data = pd.read_csv(protein_file, sep='\t')
    
    prot_comp_set = pd.merge(mol_data[["SMILES","accession", "pchembl_value_Mean"]], prot_data[["target_id","Length","Sequence"]], on="target_id")

    converter = ChemblUniprotConverter()
    
    prot_comp_set['Target_CHEMBL_ID'] = prot_comp_set['accession'].apply(converter.convert_2_chembl_id)
    
    prot_comp_set = prot_comp_set[prot_comp_set['Target_CHEMBL_ID'].str.startswith("CHEMBL")] # later add a dict for uniprot id that are merged in database
    
    prot_comp_set.columns = ["Compound_SMILES", "Target_ID", 
                             "Target_Accession", "pchembl_value_Mean", 
                             "Protein_Type", "Protein_Length", "Target_FASTA", "Target_CHEMBL_ID"]
    
    prot_comp_set["Compound_SELFIES"] = process_in_parallel(prot_comp_set["Compound_SMILES"], 19)

    prot_comp_set = prot_comp_set.dropna()
    
    if pchembl_threshold: 
        prot_comp_set = prot_comp_set[prot_comp_set["pchembl_value_Mean"] >= pchembl_threshold]
    if prot_len:
        prot_comp_set = prot_comp_set[prot_comp_set["Protein_Length"] <= prot_len]
        
    prot_comp_set[["Target_FASTA",
                   "Target_CHEMBL_ID",
                   "Compound_SELFIES"]].to_csv("./data/papyrus/prot_comp_set_pchembl_{}_protlen_{}.csv".format(pchembl_threshold,prot_len), index=False)
    

if __name__ == "__main__":
    # Create the output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)

    # Download and decompress the files
    prepare_papyrus(molecule_url, protein_url, output_directory, pchembl_threshold=None, prot_len=None)
    
    print("Papyrus data preparation complete.")