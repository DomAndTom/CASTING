import os
from datetime import timedelta
import shutil
from pathlib import Path

import fastapi as fl
import yaml
from fastapi.templating import Jinja2Templates

from . import rootdir, rootname
from .jwt_handler import create_access_token, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

api = fl.FastAPI()

page = Jinja2Templates(directory=rootdir / "pages").TemplateResponse


@api.get("/")
async def index():
    return fl.responses.RedirectResponse('/docs')


@api.get('/favicon.ico')
async def favicon():
    return fl.responses.FileResponse(
        path=rootdir / "static/favicon.ico",
        headers={"Content-Disposition": "attachment; filename=favicon.ico"},
    )


@api.get("/create-anonymous-session")
def create_anonymous_session(response: fl.Response):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"user": "anonymous"}, expires_delta=access_token_expires)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=False,
        samesite="Lax"
    )
    return {"message": "Anonymous session created", "access_token": access_token}


@api.get("/inputs/")
def query_inputs(request: fl.Request, query: str = ''):

    token = request.cookies.get("access_token") 
    if not token:
        raise fl.HTTPException(status_code=401, detail="Not authenticated")

    out = yaml.safe_load(open(rootdir / 'inputs_def.yml'))
    available = list(out.keys())

    # first level
    qs = list(Path(query).parts)
    if not qs or qs[0] not in available:
        return {"available_queries": available}
    out = out[qs[0]]
    qs += ['/'] * (query[-1] == '/')

    # subsequent levels
    for i, q in enumerate(qs[1:], 1):
        # direct descent
        if q in out:
            out = out.get(q, out)
            continue
        # options
        for s0, s1 in [('map_items', 'key'), ('input_options', 'value')]:
            available = [s[s1] for s in out.get(s0, [])]
            if not available:
                continue
            elif q not in available:
                prefix = '/'.join(qs[:i])
                available = [f"{prefix}/{s}" for s in available]
                return {"available_queries": available}
            else:
                ix = available.index(q)
                out = {'type': s0, **out[s0][ix]}
                out.pop(s1)
                break
    return {'query': query, **out}


@api.post("/file/{jobID}")
def upload_file(
    request: fl.Request,
    jobID: str,
    file: fl.UploadFile = fl.File(...),
):
    token = request.cookies.get("access_token") 
    if not token:
        raise fl.HTTPException(status_code=401, detail="Not authenticated")
    
    filedir = Path(os.environ.get(f'{rootname}_DIR', '')) / 'docs' / jobID 
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
    token = request.cookies.get("access_token") 
    if not token:
        raise fl.HTTPException(status_code=401, detail="Not authenticated")
    filedir = Path(os.environ.get(f'{rootname}_DIR', '')) / jobID
    files = [fpath.name for fpath in filedir.glob('*.*')]
    var = {"request": request, "jobID": jobID, "files": files}
    return page('ls.html', var)


@api.get("/file/{jobID}/{filename}")
def download_file(request: fl.Request, jobID: str, filename: str):
    token = request.cookies.get("access_token")
    if not token:
        raise fl.HTTPException(status_code=401, detail="Not authenticated")
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
