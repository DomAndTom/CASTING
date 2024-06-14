import os
import shutil
from pathlib import Path

import fastapi as fl
from fastapi.templating import Jinja2Templates

from . import rootdir, rootname

api = fl.FastAPI()

page = Jinja2Templates(directory=rootdir / "pages").TemplateResponse


@api.get("/")
async def index():
    return fl.responses.RedirectResponse('/docs')


@api.post("/file/{jobID}")
def upload_file(
    jobID: str,
    file: fl.UploadFile = fl.File(...),
):
    filedir = Path(os.environ.get(f'{rootname}_DIR', '')) / jobID
    filedir.mkdir(parents=True, exist_ok=True)
    fpath = filedir / file.filename
    if fpath.exists():
        return {"message": f"FileUploadError: File '{fpath}' exists."}
    try:
        with open(fpath, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    except Exception:
        return {"message": "FileUploadError"}
    finally:
        file.file.close()
    return {"message": f"Successfully uploaded '{file.filename}'."}


@api.get("/file/{jobID}")
def list_files(request: fl.Request, jobID: str):
    filedir = Path(os.environ.get(f'{rootname}_DIR', '')) / jobID
    files = [fpath.name for fpath in filedir.glob('*.*')]
    var = {"request": request, "jobID": jobID, "files": files}
    return page('ls.html', var)


@api.get("/file/{jobID}/{filename}")
def download_file(jobID: str, filename: str):
    filedir = Path(os.environ.get(f'{rootname}_DIR', '')) / jobID
    fpath = filedir / filename
    if not fpath.exists():
        return {
            "message": f"FileDownloadError: File '{fpath}' does not exists."
        }
    typ = 'application/octet-stream'
    return fl.responses.FileResponse(fpath, media_type=typ, filename=filename)


# ---------------------------------------------------------

import uvicorn


class Server(uvicorn.Server):
    """Override uvicorn.Server to handle exit."""

    def handle_exit(self, sig, frame):
        """Handle exit."""
        print('\nExiting...')
        super().handle_exit(sig=sig, frame=frame)


def run_server(
    app: str = f'{rootname}.{Path(__file__).stem}:api',
    host: str = '127.0.0.1',
    port: int = 5000,
):
    kwargs = {'app': app, 'host': host, 'port': port}
    server = Server(uvicorn.Config(**kwargs))
    server.run()


if __name__ == '__main__':
    import typer

    typer.run(run_server)
