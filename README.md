# inbs
Flask based notebook server

# Quickstart

## Installation

Install from Github or PyPi:

1. PyPi install:
```bash
python -m pip install inbs
```

2. Github install:
```bash
git clone https://github.com/NelsonSharma/inbs.git
python -m pip install ./inbs
```
* NOTE: the cloned repo can be deleted after installing

```bash
rm -Rf inbs
```


## Hosting a Server

Each server (process) has a `base` directory from which it can serve files and pages. Assuming our base directory is located at `/home/user/base`, then the start command would be:

```bash
python -m inbs --base=/home/user/base --title="Notebook Server" --home=home --host=127.0.0.1 --port=8888
```

* This would host a server on the loopback interface and can be accessed on a web browser via `http://127.0.0.1:8888`

* It also creates (if not existing) a **Home** notebook file at `/home/user/base/home.ipynb`  as specified by the `--home` argument. 
* The `--title` argument indicates the html title (of the home page) which is shown in the browser. 
* By default, the server is hosted on all available IP-Interfaces (`0.0.0.0`) but it can be modified using the `--host` argument. The port defaults to `8888` and can be changed using `--port` argument.

## Notes

#### File Access:

* The server actually exposes the `base` directory via http. Any file can be read/downloaded from within the `base` directory via a url.

* Users can request files by full http urls but directory listing is not available.

* If a user request a Notebook file (`.ipynb`), it is converted to HTML and the HTML page is sent instead.

* If the user requests any other type of file, it will be sent to the user as it is.

* Furthermore, by appending `??` to the url, users can force download a file (independent of the file-type)

* There is a limit to the size of files that can be downloaded, which is `1024MB` by default. This can be changed using the `--max_size` argument. It accepts human readable strings only, like `--max_size=100GB`. Valid units are `KB, MB, GB, TB`.
* To prevent downloading files, one can use `--no_files=1` in the start command.

#### Home Page and Links

* The **Home** Notebook can be edited on the run to include links to files and other notebooks inside the `base` directory. The links should start with a `./` (refers to the `base` directory)

* In-fact any of the notebook files can be edited on the run, however, the changes would not be reflected on the server immediately. This is because the server uses a cached copy of the notebook HTML. 

* To refresh the notebook after making changes, the server must be forced to convert the notebook to HTML again and update its cache. This can be done by appending `?!` to the url of the notebook that is to be refreshed. After refreshing, it will continue to server the new HTML page from the cache untill refreshed again.

* The cache has no limits, so it will consume RAM based on the number of new pages visited. The cache can be cleared by appending `?~` to the home url like `http://127.0.0.0:8888/?~`
