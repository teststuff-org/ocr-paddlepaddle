param(
    [string]$Command = "start",
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Écoute par défaut sur 127.0.0.1 seulement : l'API n'est joignable que depuis cette machine,
# et `http://localhost:8000/docs` répond quel que soit le navigateur.
# Pour exposer l'API sur le réseau local : $env:HOST = "0.0.0.0"
$HostAddress = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$Port = if ($env:PORT) { $env:PORT } else { 8000 }

# Rechargement à chaud DÉSACTIVÉ par défaut. Sous Windows, le reloader d'uvicorn ne peut pas
# recevoir proprement l'ordre d'arrêt quand la console n'est pas interactive : il se fige après
# "Reloading..." et laisse un worker orphelin qui garde le port et sert l'ancien code. C'est la
# cause des incidents "le port répond mais le code n'est pas celui que je viens d'écrire".
# Pour développer avec rechargement : .\run.ps1 start -Reload   (ou $env:RELOAD = "true")
$ReloadEnabled = $Reload -or ($env:RELOAD -eq "true")
$ReloadArgs = if ($ReloadEnabled) { @("--reload") } else { @() }


function Test-PortOpen {
    param([int]$TargetPort)

    $Probe = New-Object System.Net.Sockets.TcpClient
    try {
        $Probe.Connect("127.0.0.1", $TargetPort)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $Probe.Dispose()
    }
}


function Get-ProcessTree {
    # Arbre complet (racine + descendants) : tuer un maillon isolé laisse des orphelins qui
    # gardent le port et continuent de servir l'ancien code.
    param([int]$RootId)

    $Children = @{}
    foreach ($Process in Get-CimInstance Win32_Process) {
        $ParentId = [int]$Process.ParentProcessId
        if (-not $Children.ContainsKey($ParentId)) { $Children[$ParentId] = New-Object System.Collections.ArrayList }
        [void]$Children[$ParentId].Add([int]$Process.ProcessId)
    }

    $Tree = New-Object System.Collections.ArrayList
    $Queue = New-Object System.Collections.Queue
    $Queue.Enqueue([pscustomobject]@{ Id = $RootId; Depth = 0 })
    while ($Queue.Count -gt 0) {
        $Node = $Queue.Dequeue()
        [void]$Tree.Add($Node)
        if ($Children.ContainsKey($Node.Id)) {
            foreach ($ChildId in $Children[$Node.Id]) {
                $Queue.Enqueue([pscustomobject]@{ Id = $ChildId; Depth = $Node.Depth + 1 })
            }
        }
    }
    return $Tree
}


function Get-ServerProcess {
    # Renvoie le processus qui écoute sur le port, ou $null. Ignore l'entrée fantôme laissée
    # par un kill brutal : Get-NetTCPConnection peut désigner un PID déjà mort.
    param([int]$TargetPort)

    if (-not (Test-PortOpen -TargetPort $TargetPort)) { return $null }

    $Listener = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $Listener) { return $null }

    $Process = Get-Process -Id $Listener.OwningProcess -ErrorAction SilentlyContinue
    if (-not $Process) { return $null }
    return $Process
}


function Get-ApiRootProcessId {
    # Remonte la chaîne des parents tant qu'ils appartiennent à cette API. Tuer le seul processus
    # qui tient le port laisse en vie le lanceur (`uv run uvicorn`, reloader) : celui-ci peut
    # relancer un worker qui resservira l'ancien code. On arrête donc la racine de la chaîne.
    param([int]$ProcessId)

    $CurrentId = $ProcessId
    for ($Step = 0; $Step -lt 10; $Step++) {
        $Current = Get-CimInstance Win32_Process -Filter "ProcessId=$CurrentId" -ErrorAction SilentlyContinue
        if (-not $Current) { break }

        $Parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($Current.ParentProcessId)" -ErrorAction SilentlyContinue
        if (-not $Parent) { break }
        if ($Parent.CommandLine -notlike "*uvicorn*" -and $Parent.CommandLine -notlike "*app.main*") { break }

        $CurrentId = [int]$Parent.ProcessId
    }
    return $CurrentId
}


function Stop-Server {
    param([int]$TargetPort)

    $Server = Get-ServerProcess -TargetPort $TargetPort
    if (-not $Server) {
        Write-Host "Aucun serveur n'ecoute sur le port $TargetPort." -ForegroundColor Yellow
        return 0
    }

    $CommandLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($Server.Id)").CommandLine
    if ($CommandLine -notlike "*uvicorn*" -and $CommandLine -notlike "*app.main*") {
        Write-Host "Le port $TargetPort est tenu par le PID $($Server.Id), qui n'est pas cette API :" -ForegroundColor Red
        Write-Host "  $CommandLine" -ForegroundColor Red
        Write-Host "Rien n'a ete arrete. Arretez-le vous-meme si c'est voulu." -ForegroundColor Yellow
        return 1
    }

    $RootId = Get-ApiRootProcessId -ProcessId $Server.Id
    $Tree = Get-ProcessTree -RootId $RootId
    Write-Host "Arret du serveur (racine PID $RootId, $($Tree.Count) processus)..."

    # Windows n'a pas de SIGTERM pour une application console : on arrete l'arbre du plus
    # profond au plus haut. Les enfants d'abord, sinon un worker survit et garde le port.
    foreach ($Node in ($Tree | Sort-Object Depth -Descending)) {
        Stop-Process -Id $Node.Id -Force -ErrorAction SilentlyContinue
    }

    for ($Attempt = 0; $Attempt -lt 40; $Attempt++) {
        Start-Sleep -Milliseconds 250
        if (-not (Test-PortOpen -TargetPort $TargetPort)) {
            Write-Host "Serveur arrete, port $TargetPort libre." -ForegroundColor Green
            return 0
        }
    }

    Write-Host "Le port $TargetPort repond encore 10 s apres l'arret." -ForegroundColor Red
    Write-Host "Verifiez avec : Get-NetTCPConnection -LocalPort $TargetPort -State Listen" -ForegroundColor Yellow
    return 1
}


function Start-Server {
    if (Test-PortOpen -TargetPort $Port) {
        $Owner = (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).OwningProcess
        Write-Host "Port $Port deja occupe (PID $Owner)." -ForegroundColor Red
        Write-Host "Arretez-le avec : .\run.ps1 stop   (ou lancez avec : `$env:PORT = 8001)" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "API          : http://localhost:$Port"
    Write-Host "Swagger (UI) : http://localhost:$Port/docs"
    Write-Host "ReDoc        : http://localhost:$Port/redoc"
    Write-Host "Ecoute sur   : $HostAddress`:$Port"
    if ($ReloadEnabled) {
        Write-Host "Rechargement : actif (a eviter sous Windows, voir .\run.ps1 stop)" -ForegroundColor Yellow
    }
    else {
        Write-Host "Rechargement : desactive (relancez .\run.ps1 apres une modification du code)"
    }

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        if (-not (Test-Path ".venv")) { uv venv }
        uv pip install -r requirements.txt
        uv run uvicorn app.main:app --host $HostAddress --port $Port @ReloadArgs
    }
    else {
        Write-Host "uv introuvable, utilisation de venv + pip (installer uv : https://docs.astral.sh/uv/)"
        if (-not (Test-Path ".venv")) { python -m venv .venv }
        & .\.venv\Scripts\Activate.ps1
        pip install -r requirements.txt
        uvicorn app.main:app --host $HostAddress --port $Port @ReloadArgs
    }
}


switch ($Command.ToLower()) {
    "start" { Start-Server }
    "stop" { exit (Stop-Server -TargetPort $Port) }
    default {
        Write-Host "Usage : .\run.ps1 [start|stop] [-Reload]" -ForegroundColor Yellow
        Write-Host "  start    demarre l'API (defaut)"
        Write-Host "  stop     arrete l'arbre de processus qui ecoute sur le port"
        Write-Host "  -Reload  rechargement a chaud (deconseille sous Windows : workers figes)"
        Write-Host "Variables : `$env:PORT (defaut 8000), `$env:HOST (defaut 127.0.0.1), `$env:RELOAD (true|false)"
        exit 2
    }
}
