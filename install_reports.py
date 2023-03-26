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
import subprocess
import shutil
import stat

import report_repositories

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info <= (3, 6):
    raise Exception("The current version of Python is less than 3.5 which is unsupported.\n Script created/tested against python version 3.8.1. ")
else:
    pass

logfileName = "_" + os.path.basename(__file__).split('.')[0] + ".log"
defaultRegistrationLogFileName = "_registration.log" # Default log name for report registration scripts

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)

propertiesFileName = "server_properties.json"
reportRequirementsFile = "requirements.txt"
reportRegistrationFile = "registration.py"
gitCloneCommandBase = "git clone --recursive"
gitPullCommand = "git pull --recurse-submodules"
gitDescribeCommand = "git describe"

# Based on how the shell pass the arguemnts clean up the options if on a linux system
if sys.platform.startswith('linux'):
    pythonCommand = "python3"
    pipCommand = "sudo pip3"
else:
    pythonCommand = "python"
    pipCommand = "pip"    


####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser()
parser.add_argument('-server', "--server", help="Code Insight server URL - http(s)://FQDN:port")
parser.add_argument("-token", "--token", help="Auth token with admin access")
parser.add_argument("-installDir", "--installationDirctory", help="Code Insight base installation folder?")
parser.add_argument("-certificate", "--certificate", help="Path to self signed certificate")

#------------------------------------------------------------------------------------------------------------------------------
def main():

    args = parser.parse_args()
    installDir = args.installationDirctory

    installerDirectory = os.path.dirname(__file__)

    if installDir is None:
        # Get the current directory of this script to determine if it is within a Code Insight installation
        reportsDirectory = os.path.dirname(installerDirectory)

        if reportsDirectory.endswith("custom_report_scripts"):
            installDir =  os.path.dirname(reportsDirectory)
    else:
        installDir = os.path.normpath(installDir)

    reportInstallationFolder = verify_installation_directory(installDir)

    if reportInstallationFolder:
        logger.info("%s is a valid folder for report installation" %reportInstallationFolder)
        print("%s is a valid folder for report installation" %reportInstallationFolder)

    else:
        logger.error("Unable to validate Code Insight install location: %s" %installDir)
        print("Unable to validate Code Insight install location: %s" %installDir)
        print(" ** Exiting report installation script")
        sys.exit()

    # Now that we know that the install location is good is there already a properties file to use?
    propertiesFile = os.path.join(reportInstallationFolder, propertiesFileName)

    propertiesFile, storeToken = verify_properties_file(propertiesFile, args)

    reportVersions = {}

    # Now install the reports
    for repository in report_repositories.repositories:
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++")
        logger.info("    Installing: %s" %repository)
        print("    Installing: %s" %repository)

        reportName = repository.split("/")[-1].split(".")[0]  # Remove the base and .git from the repo name
        reportFolder = os.path.join(reportInstallationFolder, reportName)

        # Does the directory repo already exist?
        if os.path.isdir(reportFolder):
            logger.info("        The report folder for %s already exists. Checking for updates." %reportName)
            print("        The report folder for %s already exists. Checking for updates." %reportName)

            os.chdir(reportFolder)
            pullResponse = subprocess.run(gitPullCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            if "Already up to date." in pullResponse.stdout.decode() or  "Already up-to-date" in pullResponse.stdout.decode():
                logger.info("        The latest updates are already available.")
                print("        The latest updates are already available.")

            else:

                logger.info("        Latest updates have been pulled.")
                print("        Latest updates have been pulled.")
                
                # Since there was an update verify requiremetns are met
                sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
                logger.info("        Updating requirements")
                print("        Updating requirements")
                requirementsCommand = pipCommand + " install -r " + reportRequirementsFile
                requirementsResponse = subprocess.run(requirementsCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                logger.debug(requirementsResponse.stdout.decode())
                
                # Since there was an update update the registration
                sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
                logger.info("        Updating report registration for %s" %reportName)
                print("        Updating report registration for %s" %reportName)
                registrationCommand = pythonCommand + " " + reportRegistrationFile + " -update"
                registrationResponse = subprocess.run(registrationCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                logger.debug(registrationResponse.stdout.decode())

        else:
            logger.info("        Cloning (recursively) %s" %repository)
            print("        Cloning (recursively) %s" %repository)

            sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
            # Clone the repsoitory and bring in the submodules
        
            gitCloneCommand = gitCloneCommandBase + " " + repository + " " + reportFolder

            cloneResponse = subprocess.run(gitCloneCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logger.debug(cloneResponse.stdout.decode())

            requirementsCommand = pipCommand + " install -r " + reportRequirementsFile + " --quiet"
            registrationCommand = pythonCommand + " " + reportRegistrationFile + " -reg"
            os.chdir(reportFolder)

            sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
            logger.info("        Installing requirements")
            print("        Installing requirements")
            requirementsResponse = subprocess.run(requirementsCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logger.debug(requirementsResponse.stdout.decode())

            sys.stdout.flush()  # Ensure that the message are flushed out before the os commands
            logger.info("        Registering report %s" %reportName)
            print("        Registering report %s" %reportName)
            registrationResponse = subprocess.run(registrationCommand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            
            if "Report registration succeeded!" in registrationResponse.stdout.decode():
                print("        The report has been reigstered")
                logging.info("        The report has been reigstered")

            elif "Report registration failed!" in registrationResponse.stdout.decode():
                logger.error(registrationResponse.stdout.decode())
                print("        There was a probem encountered while attempting to register the report")
                print("            %s" %registrationResponse.stdout.decode())

                # Copy the installation log file to the installer directory
                if os.path.isfile(defaultRegistrationLogFileName):
                
                    movedLogFile = os.path.join(installerDirectory, reportName + "_installation.log")
                    logger.info("Moving report registration logfile to %s" %movedLogFile)
                    try:
                        shutil.copyfile(defaultRegistrationLogFileName, movedLogFile)
                    except:
                        logger.error("Unable to copy logfile to %s" %movedLogFile)
                else:
                    logger.error("Log file does not exist: %s" %defaultRegistrationLogFileName)

                os.chdir(reportInstallationFolder)

                try:
                    shutil.rmtree(reportFolder, onerror=change_file_read_attribute)
                    print("        Removing folder: %s" %reportFolder)
                except:
                    print("        Manually remove folder: %s" %reportFolder)
                print("        Verify server/token information and attempt to install again") 
                sanitize_properties_file(propertiesFile, storeToken)              
                sys.exit()
            else:
                print("        Unknown response while attempting to register report")
                logger.error("        Unknown response while attempting to register report")
                logger.error(registrationResponse.stdout.decode())


        # Collect the report version for summary
        reportVersion = subprocess.check_output(gitDescribeCommand, shell=True)
        reportVersions[reportName] = reportVersion.rstrip().decode()

        # Copy the installation log file to the installer directory
        if os.path.isfile(defaultRegistrationLogFileName):
        
            movedLogFile = os.path.join(installerDirectory, reportName + "_installation.log")
            logger.info("Moving report registration logfile to %s" %movedLogFile)
            print("        Moving report registration logfile to %s" %movedLogFile)
            try:
                shutil.copyfile(defaultRegistrationLogFileName, movedLogFile)
            except:
                logger.error("Unable to copy logfile to %s" %movedLogFile)
                print("Unable to copy logfile to %s" %movedLogFile)

        else:
            print("Log file does not exist: %s" %defaultRegistrationLogFileName)
            logger.error("Log file does not exist: %s" %defaultRegistrationLogFileName)

        os.chdir(reportInstallationFolder)  # Go back to the custom_report_scripts folder for the next iteration

    #----------------------------------------------
    # Now that that reports are installed remove the token from the properties file
    sanitize_properties_file(propertiesFile, storeToken)
    
    print("")
    print("**************************************")
    print("Currently Installed Reports")
    for report in sorted(reportVersions):

        print(f"    {report:70} - {reportVersions[report]:10}")


#-------------------------------------------------------------------
def verify_installation_directory(installDir):
    logger.info("Entering verify_installation_directory")

    # Was a directory supplied and if so is it valid?
    if installDir:
        if os.path.isdir(installDir):
            logger.info("    Supplied directory %s does exist" %installDir)
        else:
            logger.error("    Supplied directory %s does not exist" %installDir)
            return None
  
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
        logger.info("Creating reportInstallationFolder")
        os.mkdir(reportInstallationFolder) 

    return(reportInstallationFolder)

#-------------------------------------------------------------------
def verify_properties_file(propertiesFile, args):
    logger.info("Entering verify_properties_file")
    
    missingServer = False
    missingToken = False
    storeToken = False

    serverURL = args.server
    adminAuthToken = args.token
    certificatePath = args.certificate

    # Does the properties file alrady exist?
    if os.path.isfile(propertiesFile):
        logger.info("    Attempt to use values from %s" %propertiesFile)

        # Load the config data from the file
        try:
            filePtr = open(propertiesFile, "r")
            configData = json.load(filePtr)
            filePtr.close
        except:
            logger.warning("Properties file exists but unable process or open.")
            print("Properties file exists but unable to process or open.")
            sys.exit()

        #-----------------------------
        if serverURL is None:
            if "core.server.url" in configData:
                logger.info("Using ServerURL from properties file")
                serverURL = configData["core.server.url"]
            else:
                logger.info("ServerURL not in properties file and not provided by user")
                missingServer = True
        else:
            logger.info("Using ServerURL provided by user")
        
        #-----------------------------
        if adminAuthToken is None:
            if "core.server.token" in configData:
                if configData["core.server.token"] != "*****":
                    logger.info("Using token from properties file")
                    adminAuthToken = configData["core.server.token"]
                    # Since the installer does not save this value by default it was manually added
                    # so we need to ensure to keep it's value
                    storeToken = True
                else:
                    logger.info("Token placeholder in properties file and no value provided by user ")
                    missingToken = True
            else:
                logger.info("Token not in properties file and not provided by user")
                missingToken = True
        else:
            logger.info("Using adminAuthToken provided by user")

        #-----------------------------
        if certificatePath is None:
            if "core.server.certificate" in configData:
                certificatePath = configData["core.server.certificate"]        
        else:
            logger.info("Using adminAuthToken provided by user")

        if certificatePath is not None:
            certificatePath = os.path.normpath(certificatePath)
            os.environ["REQUESTS_CA_BUNDLE"] = certificatePath
            os.environ["SSL_CERT_FILE"] = certificatePath

    else:
        logger.info("    The properties file does not currently exist so use arguments passed from commandline")

        if adminAuthToken is None:
            missingToken = True
        
        if serverURL is None:
            # Prompt user if localhost should be used?
            print("Code Insight URL not provided or stored within properties file")
            print("If no value is provied http://localhost:8888 will be used.")
            serverURL = input("  -  Enter Server URL: ")

            if serverURL == "":
                serverURL = "http://localhost:8888"
                logger.info("        Using default value for server")

    
    # At this point there should be values for the token and server
    if missingServer and missingToken:
        logger.error("    Both the server and token values Code Insight server were not in the properties file and were not provided via the command line.")
        print("    Both the server and token values Code Insight server were not in the properties file and were not provided via the command line.")
        sys.exit()
    elif missingServer:
        logger.error("    The URL for the Code Insight server was not in the properties file and was not provided via the command line.")
        print("    The URL for the Code Insight server was not in the properties file and was not provided via the command line.")
        sys.exit()

    elif missingToken:
        logger.error("    The authorizartion token for the Code Insight server was not in the properties file and was not provided via the command line.")
        print("    The authorizartion token for the Code Insight server was not in the properties file and was not provided via the command line.")
        sys.exit()

    else:
        logger.info("    Token and server values have been provided")

    configData = {}
    configData["core.server.url"] = serverURL
    configData["core.server.token"] = adminAuthToken
    configData["core.server.certificate"] = certificatePath

    # Now write the data back to the file for the reports to use
    print("    Updating properties file: %s" %propertiesFile)
    filePtr = open(propertiesFile, 'w')
    json.dump(configData, filePtr, indent=4)
    filePtr.close

    return propertiesFile, storeToken


#-------------------------------------------------------------------
def sanitize_properties_file(propertiesFile, storeToken):
    logger.info("Entering sanitize_properties_file")

    # Open the file up to see what's there and compare to what's provided
    filePtr = open(propertiesFile, "r")
    configData = json.load(filePtr)
    filePtr.close

    if not storeToken:
        logger.info("Adding masked token placeholder for auth token properties file")
        configData["core.server.token"] = "*****"

    # Now write the data back to the file
    print("    Sanitizing properties file: %s" %propertiesFile)
    filePtr = open(propertiesFile, 'w')
    json.dump(configData, filePtr, indent=4)
    filePtr.close    

    logger.info("Exiting sanitize_properties_file")

#----------------------------------------------------------------------#     
def change_file_read_attribute(func, path, exc_info):
    os.chmod( path, stat.S_IWRITE )
    os.unlink( path )


#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  