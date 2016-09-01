#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Check the metagenomic assembly by comparing with reference genome(s) """ 

import argparse
import os
from os import listdir
from os.path import isfile, join
import sys
import subprocess
import time

def isfile(path):
    """Check if path is an existing file.
      :Parameters:
          path: Path to the file
    """
    if not os.path.isfile(path):
        if os.path.isdir(path):
            msg = "{0} is a directory".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def isdir(path):
    """Check if path is an existing file.
      :Parameters:
          path: Path to the file
    """
    if not os.path.isdir(path):
        if os.path.isfile(path):
            msg = "{0} is a file.".format(path)
            raise argparse.ArgumentTypeError(msg)
        else:
            msg = "{0} does not exist.".format(path)        
    
    return path


def config_parameters():
    """Extract program options
    """
    parser = argparse.ArgumentParser(description=__doc__,
                            usage="{0} -h [options] [arg]".format(sys.argv[0]))
    parser.add_argument('-c', '--contig_file', required=True, 
                        dest='contig_file', type=isfile, 
                        help='metagenomic contig file')                          
    parser.add_argument('-f', '--ref_folder', dest='ref_folder',
                        required=True, 
                        type=isdir, default='', help='Folder with reference .fasta files')  
    parser.add_argument('-r', dest='result_dir', type=isdir,
                        default=os.curdir + os.sep, help='Path to result '
                        'directory.')                   
    parser.add_argument('-o', dest='output_name', type=str,
                        default="assembly_summary.txt", help='Summary output table name')

    parser.add_argument('-a', dest='num_threads', type=int,
                        default=1, help='#CPU for blast and marker search')                 
               
    return parser.parse_args()    


def extract_list_ref(ref_folder):

   list_ref = []
   list_ref = [f for f in listdir(ref_folder) if os.path.isfile(join(ref_folder, f))]

   return list_ref

def compare_contigs_to_ref(contig_file, ref_folder, list_ref, result_dir):

   os.system("touch %s/ready.done" % result_dir)
   for ref in list_ref:
      complete_ref = ref_folder + "/" + ".".join(ref.split('.')[:-1]) + ".fasta" 
      genome_name = ".".join(ref.split('.')[:-1])
      print (genome_name)
      if not os.path.isfile("%s/%s.done" % (result_dir, genome_name)): 
         #nucmer comparison
         cmd = "tsub 'nucmer -l 100 {0} {1}/{2}.mc.fasta -p {1}/{2} &>{1}/{2}.log; "\
            "delta-filter -i 95 -l 100 {1}/{2}.delta > {1}/{2}.delta.filt; "\
            "dnadiff -d {1}/{2}.delta.filt -p {1}/{2} &>>{1}/{2}.log 2>&1; "\
            "touch {1}/{2}.done' -q throughput -l nodes=1:ppn=1,mem=10gb"\
            ",walltime=00:30:00".format(complete_ref,result_dir,genome_name)
         os.system(cmd)


def create_report_file(list_ref, result_dir, output_name):

   #wait till all report files are generated
   nb_genome = len(list_ref)

   process_cmd = subprocess.Popen('ls {0}/*.done | wc -l'.format(result_dir),
                                  shell=True, stdout=subprocess.PIPE)
   
   nb_done = int(process_cmd.communicate()[0])
   
   while nb_done < nb_genome+1:
      print ("waiting for report files...")
      time.sleep(10)
      process_cmd = subprocess.Popen('ls {0}/*.done | wc -l'.format(result_dir),
                                  shell=True, stdout=subprocess.PIPE)
      nb_done = int(process_cmd.communicate()[0])

   with open (output_name, 'wt') as output_file:
      output_file.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % ("genome_name", 
                        "nb_contig", "total_ref_bases", "aligned_bases", "%_ref_recovered", 
                        "%_avg_identity", "avg_alignment_len", "total_snps", 
                        "total_gsnps"))
      
      for ref in list_ref:
         genome_name = ".".join(ref.split('.')[:-1])
         report_file_name = result_dir + "/" + genome_name + ".report"
         nb_contig="NA"
         total_ref_bases="NA"
         perc_recovered_ref = 0.0
         aligned_bases = "NA"
         avg_identity = "NA"
         avg_alignment_len = "NA"
         total_snps= "NA"
         total_gsnps = "NA"
 
         with open(report_file_name,'rt') as report_file:
            for line in report_file:
               if "AlignedSeqs" in line:
                  nb_contig = line.split()[2].strip().split('(')[0]
               elif "TotalBases" in line:
                  total_ref_bases = line.split()[1].strip()
               elif "AlignedBases" in line:
                  aligned_bases = line.split()[1].strip().split('(')[0]
               elif ("AvgLength" in line) and (avg_alignment_len == "NA"):
                  avg_alignment_len = line.split()[1].strip()
               elif ("AvgIdentity" in line) and (avg_identity == "NA"):
                  avg_identity = line.split()[2].strip()
               elif "TotalSNPs" in line:
                  total_snps = line.split()[2].strip()
               elif "TotalGSNPs" in line:
                  total_gsnps = line.split()[2].strip()
            perc_recovered_ref = (float(aligned_bases) / float(total_ref_bases)) * 100
            output_file.write("%s\t%s\t%s\t%s\t%.4f\t%s\t%s\t%s\t%s\n" % (
                              genome_name, nb_contig, total_ref_bases, aligned_bases, 
                              perc_recovered_ref, avg_identity,
                              avg_alignment_len, total_snps, total_gsnps))

   os.system("rm {0}/*.delta {0}/*.1delta {0}/*.qdiff {0}/*.rdiff {0}/*.snps"\
             " {0}/*.unqry {0}/*.mcoords {0}/*.mdelta {0}/*.delta.filt"\
             " {0}/*.1coords ".format(result_dir))


def create_contig_files(contig_file, ref_folder, list_ref, result_dir):
   contig_to_ref = {}

   #one liner fasta
   os.system("awk '!/^>/ {{ printf \"%s\",$0;n=\"\\n\" }} /^>/ {{ print n $0; n=\"\" }} END {{ printf \"%s\",n }}'"\
             " {0} > {1}/mc.oneline.fasta".format(contig_file, result_dir))

   #create ref db that contain all reference
   for genome in list_ref:
      genome_name = genome.replace(".fasta","")
      os.system("sed 's/>/>{0} /g' {1}/{0}.fasta >> {2}/reference.fasta".format(
                                           genome_name,ref_folder, result_dir))

   print('align sequences...')
   os.system("makeblastdb -in {0}/reference.fasta -out {0}/reference -dbtype nucl".format(result_dir))
   os.system("blastn -db {0}/reference -query {1} -word_size 100 -evalue 1e-3"\
                " -max_target_seqs 1 -perc_identity 95 -outfmt 6 -out {0}/contig_to_ref.blastn".format(
                result_dir, contig_file))

   print('extract contig reference best-hit')
   with open(result_dir + '/contig_to_ref.blastn', 'rt') as blast_file:
      for line in blast_file:
         items=line.split()
         contig_name = items[0].strip()
         ref_name = items[1].strip()
         if not contig_to_ref.get(contig_name):
            contig_to_ref[contig_name] = ref_name

   print('create fasta file for each ref')
   for genome in list_ref:
      genome_name = genome.replace(".fasta","")
      for contig in contig_to_ref:
         if contig_to_ref[contig] == genome_name:
            cmd = 'grep "^>{0}" -A 1 -m 1 {1}/mc.oneline.fasta >> {1}/{2}.mc.fasta'.format(
               contig, result_dir, genome_name)
            os.system(cmd)                 
      
      
def main():

   """Main program function
   """
               
   #Extract arguments
   args = config_parameters()

   if not os.path.isdir(args.result_dir):
      os.system("mkdir %s" % args.result_dir)

   list_ref = extract_list_ref(args.ref_folder)

   #create metaG contig files
   create_contig_files(args.contig_file, args.ref_folder, list_ref, args.result_dir)

   #compare each contigs to ref
   compare_contigs_to_ref(args.contig_file, args.ref_folder, list_ref, args.result_dir)      

   #create report file
   create_report_file(list_ref, args.result_dir, args.output_name)
                       
   print ('end')
                                                                   
if __name__ == '__main__':
    main()

