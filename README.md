# CloneMultipleRepos
<br>
This script clones multiple repos from a gitlab url in parallel. <br>
<br>
## Usage <br>
CloneMultipleRepos.py -a [server] -d [dest dir path] {flags} <br>
 -a, --gitlab_addr=    : Gitlab-Server name or ip. Valid formats: {http://ipOrName, https://ipOrName, ip, name} <br>
 -t, --gitlab_token=   : Gitlab-Access token. Needed for private repos. <br>
<br>
 -r, --repos_list=     : List of repo names separated by comma to clone. <br>
 -d, --dest_path=      : Destination path to clone repos to. <br>
<br>
 -s, --silent          : Silent mode - no user interaction. <br>
<br>
 -h, --help            : print this help message and exit <br>
<br>
Run Examples<br>
  Help:           CloneMultipleRepos.py -h <br>
  With token:     CloneMultipleRepos.py -a gitlab -t myAccessToken -d C:\myrepos --repos_list=repo1,repo2,repo3 <br>
  Without token:  CloneMultipleRepos.py -a http://gitlab -d C:\myrepos --repos_list=repo1,repo2,repo3 <br>
  Specify Port:   CloneMultipleRepos.py -a gitlab:80 -t myAccessToken -d C:\myrepos --repos_list=repo1,repo2,repo3 --silent <br>
  Silent:         CloneMultipleRepos.py -a gitlab -t myAccessToken -d C:\myrepos --repos_list=repo1,repo2,repo3 --silent <br>
