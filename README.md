#Acquisition of expressions and targets lexicons from a domain#


This toolkit allows to generate domain specific lexicons:
* Polarity or expression lexicons: lexicons with words in the specific domain used to state opinions
* Target or property lexicons: lexicons with expressions that represent properties of the entities
represented in the given domain (for a hotel review domain, these properties could be the rooms, the staff
or the ambience). 

Usually the polarity expressions are used to give opinions about properties.

Two approaches for automatically generating these domains have been implemented
and are available within this toolkit:
* Supervised acquisition: from domain annotated data
* Unsupervised acquisition: from raw data belonging to the domain

##Supervised Acquisition##

This approach is implemented in the script `acquire_from_annotated_data.py`. It basically takes as input
a set of KAF/NAF files annotated with opinions (targets, holders and expressions), and generates 2 CSV
output files with the most relevant expressions and targets. You can call directly to the script with
the option -h or --help to see the parameters:

```shell
$ acquire_from_annotated_data.py -h
usage: acquire_from_annotated_data.py [-h] (-l file_with_list | -f folder)
                                      -exp_csv expressions_file.csv -tar_csv
                                      targets_file.csv

Extract expressions and targets from annotated data

optional arguments:
  -h, --help            show this help message and exit
  -l file_with_list, --list file_with_list
                        A file with a list of paths to KAF/NAF files
  -f folder, --folder folder
                        A folder with KAF/NAF files
  -exp_csv expressions_file.csv
                        CSV file to store the expressions
  -tar_csv targets_file.csv
                        CSV file to store the targets

```

The input KAF/NAF files can be specified using in 2 exclusive ways:
* Providing a file which contains a list of paths to the annotated files (one per line) (option -l / --list)
* Providing a folder which contains the annotated files, all files with extension .kaf or .naf will be processed
(option -f / --folder)

There are two mandatory output parameters to specify where the expression and targets lexicons must be stored (the
options -exp_cvs and -tar_csv. 

The script also prints the lexicons on the standard output in a more user readable way, as well as some debugging
information on the error output. One example of usage of this program would be:

```shell
acquire_from_annotated_data.py -f ~/data/hotel -exp_csv my_expressions.csv -tar_csv my_targets.csv > log.out 2> log.err
```

This would read all the KAF/NAF files in the folder ~/data/hole and store the output in the file log.out, the debugging information in the file log.err, and the resulting
lexicons in CSV format on the files my_expressions.csv and my_targets.csv respectively.

##Unsupervised Acquisition##

##Contact##
* Ruben Izquierdo
* Vrije University of Amsterdam
* ruben.izquierdobevia@vu.nl