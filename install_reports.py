'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Mon Nov 08 2021
File : install_reports.py
'''
import sys
import os
import logging
import argparse
import json
from git import Repo
import subprocess


repositories = []
repositories.append("https://github.com/flexera/sca-codeinsight-reports-project-inventory.git")
repositories.append("git@github.com:flexera/sca-codeinsight-reports-project-sbom.git")

propertiesFileName = "server_properties.json"

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info <= (3, 6):
    raise Exception("The current version of Python is less than 3.5 which is unsupported.\n Script created/tested against python version 3.8.1. ")
else:
    pass

logfileName = os.path.dirname(os.path.realpath(__file__)) + "/_install_reports.log"


###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module



####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser()
parser.add_argument('-server', "--server", help="Code Insight server URL")
parser.add_argument("-token", "--token", help="Auth token with admin access")
parser.add_argument("-installDir", "--installationDirctory", help="Code Insight base installation folder?")


#------------------------------------------------------------------------------------------------------------------------------
def main():

    # See what if any arguments were provided
    args = parser.parse_args()
    serverURL = args.server
    adminAuthToken = args.token
    installDir = args.installationDirctory

    reportVersions = {}

    # verify the supplied installDir or current directoyr is valid
    reportInstallationFolder = verify_installation_directory(installDir)

    if reportInstallationFolder:
        logger.info("%s is a valid folder for report installation" %reportInstallationFolder)
        print("%s is a valid folder for report installation" %reportInstallationFolder)

    else:
        logger.error("Unable to determine valid Code Insight install folder for reports")
        print("Unable to determine valid Code Insight install folder for reports")
        return


    propertiesFile = os.path.join(reportInstallationFolder, propertiesFileName)

    # Does a properties file already exist? 
    propertiesFile = verify_properties_file(serverURL, adminAuthToken, propertiesFile)

    if not propertiesFile:
        logger.error("Invalid server properties file details")
        print("Invalid server properties file details")
        return

    # Now install the reports
    for repository in repositories:
        logger.info("Installing: %s" %repository)
        print("Installing: %s" %repository)

        reportName = repository.split("/")[-1].split(".")[0]  # Remove the base and .git from the repo name
        reportFolder = os.path.join(reportInstallationFolder, reportName)

        # Does the directory repo already exist?

        if os.path.isdir(reportFolder):
            logger.warning("The report folder for %s already exists." %reportName)
            print("The report folder for %s already exists." %reportName)
            # TODO - Upgrade??

        else:
            logger.info("    Cloning (recursively) %s" %repository)
            print("    Cloning (recursively) %s" %repository)

            # Clone the repsoitory and bring in the submodules
            Repo.clone_from(repository, reportFolder, recursive=True)

            requirementsFile = "requirements.txt"
            registrationFile = "registration.py"
            
            # Based on how the shell pass the arguemnts clean up the options if on a linux system:w
            if sys.platform.startswith('linux'):
                pythonCommand = "python3"
                pipCommand = "sudo pip3"
            else:
                pythonCommand = "python"
                pipCommand = "pip"                

            requirementsCommand = pipCommand + " install -r " + requirementsFile
            registrationCommand = pythonCommand + " " + registrationFile + " -reg"
            os.chdir(reportFolder)

            logger.info("    Installing requirements")
            print("    Installing requirements")
            os.system(requirementsCommand)

            logger.info("    Registering report %s" %reportName)
            print("    Registering report %s" %reportName)
            os.system(registrationCommand)

            os.chdir(reportInstallationFolder)  # Go back to the custom_report_scripts folder for the next iteration

        # For each report grab the associated version to inform the user as to what is currently installed
        versionCommand = "git -C " + reportFolder + " describe"

        reportVersion = subprocess.check_output(versionCommand, shell=True)
        reportVersions[reportName] = reportVersion.rstrip().decode()


    #----------------------------------------------

    print("**************************************")
    print("Currently Installed Reports")
    for report in sorted(reportVersions):

        print(f"    {report:50} - {reportVersions[report]:10}")




#-------------------------------------------------------------------
def verify_installation_directory(installDir):
    logger.info("Entering verify_installation_directory")

    # Was a directory supplied and if so is it valid?
    if  installDir:
        if os.path.isdir(installDir):
            logger.info("    Supplied directory %s  does exist" %installDir)
        else:
            logger.error("    Supplied directory %s does not exist" %installDir)
            return None

    else:
        logger.info("No installation directory passed.  Using current directory.")
        installDir = os.path.dirname(os.path.realpath(__file__))  # Get the current folder
        logger.info("Current directory: %s" %installDir)


    # At this point we are assuming we have the Code Insight instllation folder or possibly the custom_report_scripts folder
    if installDir.endswith("custom_report_scripts"):
        logger.info("The customer_report_script directory could have been passed directly")
        installDir = installDir[:-22]  # Strip off custom_report_scripts part
    

    # A list of folders that we expect to see within the Code Insight base instllation folder
    expectedFolders = ["tomcat", "jre", "logs", "7-zip", "dbScripts"]
    folders = os.listdir(installDir)

    if not set(expectedFolders).issubset(set(folders)):
        # This doesn't look like a Code Insight folder
        logger.error("This does not appear to be a Code Insight installation")
        return None

    reportInstallationFolder = os.path.join(installDir, "custom_report_scripts")

    # Does the custom_report_scripts folder exist?
    if os.path.isdir(reportInstallationFolder):
        logger.info("reportInstallationFolder already exists")
    else:
        os.mkdir(reportInstallationFolder) 

    return(reportInstallationFolder)

#-------------------------------------------------------------------
def verify_properties_file(serverURL, adminAuthToken, propertiesFile):
    logger.info("Entering verify_properties_file")
   
    # Does the properties file alrady exist?
    if not os.path.isfile(propertiesFile):
        logger.info("    The properties file does not currently exist")

        # Were values passed by the users?
        if serverURL and adminAuthToken:

            # Deal with server configuration values
            serverDetails={}
            serverDetails["core.server.url"]=serverURL
            serverDetails["core.server.token"]=adminAuthToken

            print("    Creating properties file: %s" %propertiesFile)
            filePtr = open(propertiesFile, 'w')
            json.dump(serverDetails, filePtr)
            filePtr.close

        else:
            logger.error("    The URL or token values were not provided")
            print("    The URL or token values were not provided")
            return None

    else:
        logger.info("    %s already exists" %propertiesFile)
        print("    %s already exists" %propertiesFile)

    return propertiesFile

    #TODO  Check the values passed to values in the file currently and prompt for update if needed





#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  