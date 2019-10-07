import ntpath
import re
import sys
import getopt
import json
import shlex
from urllib.request import urlopen
from subprocess import Popen

# Global Vars
scriptDir = ntpath.split(sys.argv[0])[0]
scriptName = ntpath.basename(sys.argv[0])

gitlabAddr = ''
gitlabToken = ''
reposList = ''
destPath = ''
isSilent = False


class Repo:
    def __init__(self, repoName, http_url_to_repo=None, isCloned=False, cloneToPath=None, cloneCommand=None):
        self.repoName = repoName
        self.http_url_to_repo = http_url_to_repo
        self.isCloned = isCloned
        self.cloneToPath = cloneToPath
        self.cloneCommand = cloneCommand


def prepareHelpString():
    global scriptName

    # Prepare help string
    helpStr = "\n"
    helpStr += "This script clones multiple repos from a gitlab url.\n\n"
    helpStr += "Usage:\n"
    helpStr += scriptName + " -a <server> -u <user> -p <pass> -d <dest dir path> [flags] \n"
    helpStr += " -a, --gitlab_addr=    : Gitlab-Server name or ip. Valid formats: [http://ipOrName, https://ipOrName, ip, name]\n"
    helpStr += " -t, --gitlab_token=   : Gitlab-Access token. Needed for private repos.\n"

    helpStr += " -r, --repos_list=     : List of repo names separated by comma to clone.\n"
    helpStr += " -d, --dest_path=      : Destination path to clone repos to.\n"

    helpStr += " -s, --silent          : Silent mode - no user interaction.\n"

    helpStr += " -h, --help            : print this help message and exit\n\n"

    helpStr += "Run Examples\n"
    helpStr += "  Help:           " + scriptName + " -h\n"
    helpStr += "  With token:     " + scriptName + " -a gitlab -t myAccessToken -d C:\\myrepos --repos_list=repo1,repo2,repo3\n"
    helpStr += "  Without token:  " + scriptName + " -a http://gitlab -d C:\\myrepos --repos_list=repo1,repo2,repo3 \n"
    helpStr += "  Specify Port:   " + scriptName + " -a gitlab:80 -t myAccessToken -d C:\\myrepos --repos_list=repo1,repo2,repo3\n"
    helpStr += "  Silent:         " + scriptName + " -a gitlab -t myAccessToken -d C:\\myrepos --repos_list=repo1,repo2,repo3 --silent\n"

    return helpStr


def askIfSure(destPath):
    info = '\nCloning found repos to:\n{}\n'.format(destPath)
    question = 'Are you sure?'
    msg = '\n'.join([info,question])
    validChoices = {"y": True, "n": False}
    return raiseQuestionToUser(msg, validChoices, default='y')

def raiseQuestionToUser(question, validChoices, default=None):
    # validChoices - must be a json of the form: {"yes": True,"y": True, "no": False, "n": False}

    prompt = " [{}] ".format("/".join(validChoices.keys()))
    if not default in validChoices.keys():
        print('Error - default={} for raiseQuestionToUser() function is not one of the valid choices: {}'.format(default, validChoices.keys()))
        return None

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return validChoices[default]
        elif choice in validChoices:
            return validChoices[choice]
        else:
            goodResponses = "' or '".join(validChoices.keys())
            sys.stdout.write("Please respond with: '{}'\n".format(goodResponses))

def readCommandLineArgs(argv):
    global scriptName
    global helpStr

    helpStr = prepareHelpString();

    # Attempt to prepare reading params object
    try:
        opts, args = getopt.getopt(argv, "hsa:t:r:d:", ["gitlab_addr=",
                                                        "gitlab_token=",
                                                        "repos_list=",
                                                        "dest_path=",
                                                        "silent",
                                                        "help"])
    except getopt.GetoptError as errorMsg:
        print("\nError preparing 'getopt' object:\n" + str(errorMsg) + "\n")
        print(helpStr)
        sys.exit(2)

    global gitlabAddr
    global gitlabToken
    global reposList
    global destPath
    global isSilent

    receivedArgs = ''

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            terminateProgram(0, helpStr)
        elif opt in ("-a", "--ftp_addr"):
            gitlabAddr = arg
        elif opt in ("-t", "--gitlab_token"):
            gitlabToken = arg
        elif opt in ("-r", "--repos_list"):
            reposList = arg
        elif opt in ("-d", "--dest"):
            destPath = arg
        elif opt in ("-s", "--silent"):
            isSilent = True
        else:
            errorMsg = "Error - unexpected arg: '" + arg + "'\n" + helpStr
            terminateProgram(1, errorMsg)

        receivedArgs += '{} {} '.format(opt, arg)

    return receivedArgs


def checkParams():
    global gitlabAddr
    global destPath
    global reposList

    # Must have at least address, user, pass, src and dest paths
    if not (gitlabAddr and destPath and reposList):
        errorMsg = "Please provide the following:\n-a gitlab_addr -d dest_path --repos_list=repo1,repo2,repo3\n" + helpStr
        terminateProgram(1, errorMsg)

    gitlabAddrLowered = str(gitlabAddr).lower()
    if not ('http://' in gitlabAddrLowered or 'https://' in gitlabAddrLowered):
        gitlabAddr = 'http://{}'.format(gitlabAddrLowered)

    if gitlabAddr[len(gitlabAddr)-1] == '/':
        gitlabAddr = gitlabAddr[:-1]

    return True


def terminateProgram(exitCode, msg=''):
    print('Aborting..\n{}'.format(msg))
    sys.exit(exitCode)


def parseCommandLineReposList(reposList):
    reposListArr = str(reposList).split(',')
    return [x for x in reposListArr]


def getAllProjectsDic(urlStr):
    global gitlabToken
    try:
        urlStrFull = "{}/api/v4/projects?".format(urlStr)
        if gitlabToken:
            urlStrFull += "private_token={}".format(gitlabToken)
        urlStrFull += "&per_page=100000"
        projectsUrl = urlopen(urlStrFull)
        allProjectsDict = json.loads(projectsUrl.read().decode())
        return allProjectsDict
    except BaseException as errorMsg:
        print('Failed getting all projects list from: {}\nError:\n{}'.format(urlStrFull, errorMsg))
        return None


def convertToReposObjList(allProjectsDict, reposList):
    reposToDownloadObjList = []
    i = 0
    endInd = len(reposList)
    while(i < endInd):
        repoName = reposList[i]

        for project in allProjectsDict:
            projectName = project['name']
            if projectName is None:
                continue

            projectName = str(projectName).lower()
            if repoName.lower() == projectName:
                http_url_to_repo = project['http_url_to_repo']
                if http_url_to_repo is None:
                    print('Error - cannot clone project "{}" because its http_url_to_repo var is None'.format(repoName))
                    reposToDownloadObjList.append(Repo(repoName))
                    break;
                reposToDownloadObjList.append(Repo(repoName, http_url_to_repo))
                break;
        i += 1

    return reposToDownloadObjList


def setReposCloneCommands(reposObjList):
    global destPath

    for repoObj in reposObjList:
        thisRepoURL = repoObj.http_url_to_repo
        if thisRepoURL is None:
            continue
        repoName = repoObj.repoName
        fullDestPath = destPath + '/' + repoName

        cloneCommand = shlex.split('git clone {} "{}"'.format(thisRepoURL, fullDestPath))
        repoObj.cloneCommand = cloneCommand
        repoObj.cloneToPath = fullDestPath


def startSubProcessesClonings(reposObjList):
    overallSuccess = True
    try:
        subProcCount = len(reposObjList)
        print("Starting {} sub-processes to clone the repos".format(subProcCount))
        procsAndRepos = [(Popen(x.cloneCommand), x) for x in reposObjList]

        print("Waiting for processes to finish...")
        for tup in procsAndRepos:
            subProc = tup[0]
            repoObj = tup[1]
            subProc.wait()
            if subProc.returncode == 0:
                repoObj.isCloned = True
                print("Cloned {} successfuly".format(repoObj.repoName))
            else:
                print("Failed cloning {}".format(repoObj.repoName))
                overallSuccess = False

    except BaseException as errorMsg:
        print("Failed starting sub-processes\nError:\n{}".format(errorMsg))
        return False

    return overallSuccess


def printSummary(reposObjList):
    summaryStr = '\n'
    summaryStr += 'Repo     |      Clone Result\n'
    summaryStr += '-----------------------------\n'

    for repo in reposObjList:
        if repo.isCloned:
            summaryStr += '{}    -    {}  [{}]\n'.format(repo.repoName, repo.isCloned, repo.cloneToPath)
        else:
            summaryStr += '{}    -    {}\n'.format(repo.repoName, repo.isCloned)

    summaryStr += "\n"
    print(summaryStr)

def main():
    global gitlabAddr
    global gitlabUser
    global gitlabPassword
    global reposList

    receivedArgs = readCommandLineArgs(sys.argv[1:])
    print('Clone Multiple Repos - Started')
    print('Command Line: {} {}\n'.format(sys.argv[0], receivedArgs))

    # Check that params are ok
    if not checkParams():
        terminateProgram(1)

    parsedReposList = parseCommandLineReposList(reposList)
    if parsedReposList is None or len(parsedReposList) == 0:
        terminateProgram(1)

    allProjectsDict = getAllProjectsDic(gitlabAddr)
    if allProjectsDict is None:
        terminateProgram(1)

    reposObjList = convertToReposObjList(allProjectsDict, parsedReposList)
    if len(reposObjList) == 0:
        print('Could not find requested repos on {} repo list.\nMight need to provide access token to get full list of repos'.format(gitlabAddr))
        terminateProgram(1)
    else:
        print('Found {} repos on {} repo list.'.format(len(reposObjList), gitlabAddr))

    setReposCloneCommands(reposObjList)

    if not isSilent and not askIfSure(destPath):
        terminateProgram(0)

    cloningProcess = startSubProcessesClonings(reposObjList)
    printSummary(reposObjList)

    if cloningProcess:
        print('Finished cloning successfuly')
    else:
        print('Failed cloning repos list')

    print('Clone Multiple Repos - Finished')


main()
