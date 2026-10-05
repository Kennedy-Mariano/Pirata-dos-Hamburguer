# ============================================================================
# iniciar.ps1  --  liga TUDO do DeliveryBot com um clique.
#
# Normalmente voce NAO roda este arquivo direto: de duplo clique em
# "Iniciar DeliveryBot.bat" (mesma pasta).
#
# O que ele faz, em ordem:
#   1. Prepara o ambiente na primeira vez (.env, Python, segredos).
#   2. Pede a SENHA DA COZINHA numa janela do Windows (so na primeira vez) e
#      guarda protegida pelo Windows (DPAPI) -- nunca em texto no .env.
#   3. Abre o Docker Desktop sozinho (se estiver fechado) e sobe o WAHA.
#   4. Abre o ngrok e atualiza o BASE_URL.
#   5. Liga o sistema (Flask).
#   6. Abre no navegador a pagina do QR Code do WhatsApp e espera conectar.
# ============================================================================
param([switch]$SoTrocarSenha, [switch]$ConfigurarIA)

$ErrorActionPreference = "Stop"
$pastaProjeto = $PSScriptRoot
Set-Location $pastaProjeto

$utf8SemBom = New-Object System.Text.UTF8Encoding($false)

function Escrever($texto, $cor = "White") { Write-Host $texto -ForegroundColor $cor }

function Ler-Texto($caminho) {
    return ([System.IO.File]::ReadAllText($caminho, $utf8SemBom)) -replace "`r`n", "`n"
}
function Gravar-Texto($caminho, $texto) {
    [System.IO.File]::WriteAllText($caminho, $texto, $utf8SemBom)
}

function Gerar-Segredo([int]$tamanho = 28) {
    $caracteres = (48..57) + (65..90) + (97..122)
    -join (1..$tamanho | ForEach-Object { [char]($caracteres | Get-Random) })
}

function Ler-VariavelEnv($nome) {
    $conteudo = Ler-Texto $envPath
    if ($conteudo -match "(?m)^$nome=(.*)$") { return $matches[1].Trim() }
    return ""
}

# Troca (ou cria) NOME=valor no .env, sem mexer no resto do arquivo.
function Definir-VariavelEnv($nome, $valor) {
    $linhas = (Ler-Texto $envPath) -split "`n"
    $achou = $false
    $novas = foreach ($l in $linhas) {
        if ($l -match "^$nome=") { $achou = $true; "$nome=$valor" } else { $l }
    }
    $texto = ($novas -join "`n")
    if (-not $achou) { $texto = $texto.TrimEnd("`n") + "`n$nome=$valor`n" }
    Gravar-Texto $envPath $texto
}

function Comando-Existe($nome) { return [bool](Get-Command $nome -ErrorAction SilentlyContinue) }

# ---------------------------------------------------------------------------
# Senha da cozinha protegida pelo Windows (DPAPI)
# Fica em data\cozinha.senha, criptografada com a conta do Windows deste
# notebook: copiar o arquivo para outro PC/usuario nao serve pra nada.
# ---------------------------------------------------------------------------
$arquivoSenha = Join-Path $pastaProjeto "data\cozinha.senha"

function SecureString-ParaTexto([System.Security.SecureString]$s) {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Pedir-NovaSenhaCozinha {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
    } catch { return $null }

    while ($true) {
        $f = New-Object System.Windows.Forms.Form
        $f.Text = "DeliveryBot - Senha da cozinha"
        $f.StartPosition = "CenterScreen"; $f.TopMost = $true
        $f.FormBorderStyle = "FixedDialog"; $f.MaximizeBox = $false; $f.MinimizeBox = $false
        $f.ClientSize = New-Object System.Drawing.Size(380, 235)
        $f.Font = New-Object System.Drawing.Font("Segoe UI", 10)

        $t = New-Object System.Windows.Forms.Label
        $t.Text = "Crie a senha do painel da cozinha.`nEla sera pedida ao abrir /cozinha (usuario: admin).`nMinimo 6 caracteres."
        $t.Location = New-Object System.Drawing.Point(15, 12); $t.Size = New-Object System.Drawing.Size(350, 60)

        $l1 = New-Object System.Windows.Forms.Label; $l1.Text = "Senha:"
        $l1.Location = New-Object System.Drawing.Point(15, 80); $l1.Size = New-Object System.Drawing.Size(120, 22)
        $c1 = New-Object System.Windows.Forms.TextBox; $c1.UseSystemPasswordChar = $true
        $c1.Location = New-Object System.Drawing.Point(140, 78); $c1.Size = New-Object System.Drawing.Size(220, 25)

        $l2 = New-Object System.Windows.Forms.Label; $l2.Text = "Repita a senha:"
        $l2.Location = New-Object System.Drawing.Point(15, 120); $l2.Size = New-Object System.Drawing.Size(120, 22)
        $c2 = New-Object System.Windows.Forms.TextBox; $c2.UseSystemPasswordChar = $true
        $c2.Location = New-Object System.Drawing.Point(140, 118); $c2.Size = New-Object System.Drawing.Size(220, 25)

        $aviso = New-Object System.Windows.Forms.Label; $aviso.ForeColor = [System.Drawing.Color]::Firebrick
        $aviso.Location = New-Object System.Drawing.Point(15, 155); $aviso.Size = New-Object System.Drawing.Size(350, 22)

        $ok = New-Object System.Windows.Forms.Button; $ok.Text = "Salvar"
        $ok.Location = New-Object System.Drawing.Point(180, 190); $ok.Size = New-Object System.Drawing.Size(85, 30)
        $ok.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $cancel = New-Object System.Windows.Forms.Button; $cancel.Text = "Cancelar"
        $cancel.Location = New-Object System.Drawing.Point(275, 190); $cancel.Size = New-Object System.Drawing.Size(85, 30)
        $cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel

        $f.AcceptButton = $ok; $f.CancelButton = $cancel
        $f.Controls.AddRange(@($t, $l1, $c1, $l2, $c2, $aviso, $ok, $cancel))
        $f.Add_Shown({ $c1.Focus() })

        # valida sem fechar a janela
        $ok.Add_Click({
            if ($c1.Text.Length -lt 6) { $aviso.Text = "A senha precisa ter pelo menos 6 caracteres."; $f.DialogResult = [System.Windows.Forms.DialogResult]::None }
            elseif ($c1.Text -ne $c2.Text) { $aviso.Text = "As duas senhas nao sao iguais."; $f.DialogResult = [System.Windows.Forms.DialogResult]::None }
        })

        $r = $f.ShowDialog()
        $senha = $c1.Text
        $f.Dispose()
        if ($r -ne [System.Windows.Forms.DialogResult]::OK) { return $null }
        return $senha
    }
}

function Definir-SenhaCozinha {
    $senha = Pedir-NovaSenhaCozinha
    if (-not $senha) {
        # Sem ambiente grafico: cai para o console (digitacao oculta).
        $a = Read-Host "Crie a senha da cozinha (min. 6 caracteres)" -AsSecureString
        $senha = SecureString-ParaTexto $a
        if ($senha.Length -lt 6) { return $false }
    }
    $seguro = ConvertTo-SecureString $senha -AsPlainText -Force
    New-Item -ItemType Directory -Force -Path (Split-Path $arquivoSenha) | Out-Null
    ($seguro | ConvertFrom-SecureString) | Set-Content -Path $arquivoSenha -Encoding ASCII
    return $true
}

function Carregar-SenhaCozinha {
    if (-not (Test-Path $arquivoSenha)) { return $null }
    try {
        $seguro = (Get-Content $arquivoSenha -Raw).Trim() | ConvertTo-SecureString
        return SecureString-ParaTexto $seguro
    } catch { return $null }   # arquivo de outro usuario/PC: pede de novo
}

# ---------------------------------------------------------------------------
# IA do atendimento (conversa natural). A chave do Claude tambem fica
# protegida pelo Windows (DPAPI), em data\anthropic.chave -- nao no .env.
# ---------------------------------------------------------------------------
$arquivoChaveIA = Join-Path $pastaProjeto "data\anthropic.chave"

function Carregar-ChaveIA {
    if (-not (Test-Path $arquivoChaveIA)) { return $null }
    try { return SecureString-ParaTexto ((Get-Content $arquivoChaveIA -Raw).Trim() | ConvertTo-SecureString) }
    catch { return $null }
}

# Instala (se faltar), liga e prepara o Ollama + modelo. Retorna $true se pronto.
function Garantir-Ollama {
    function Atualizar-PathOllama {
        foreach ($d in @("$env:LOCALAPPDATA\Programs\Ollama", "$env:ProgramFiles\Ollama")) {
            if ((Test-Path "$d\ollama.exe") -and ($env:Path -notlike "*$d*")) { $env:Path += ";$d" }
        }
    }
    Atualizar-PathOllama

    if (-not (Comando-Existe "ollama")) {
        if (Comando-Existe "winget") {
            Escrever "Instalando o Ollama (pode pedir permissao do Windows)..." "Cyan"
            cmd /c "winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements"
            Atualizar-PathOllama
        }
        if (-not (Comando-Existe "ollama")) {
            Escrever "Nao consegui instalar o Ollama sozinho. Vou abrir a pagina de download." "Yellow"
            Escrever "Instale (Next, Next, Install), e abra o Iniciar DeliveryBot de novo." "Yellow"
            Start-Process "https://ollama.com/download/windows"
            return $false
        }
    }

    # servidor do Ollama no ar?
    cmd /c "ollama list >nul 2>&1"
    if ($LASTEXITCODE -ne 0) {
        Escrever "Ligando o Ollama..." "Cyan"
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Seconds 2
            cmd /c "ollama list >nul 2>&1"
            if ($LASTEXITCODE -eq 0) { break }
        }
        if ($LASTEXITCODE -ne 0) { Escrever "O Ollama nao ligou. Abra o aplicativo 'Ollama' no menu Iniciar e tente de novo." "Red"; return $false }
    }

    # escolhe o modelo pela memoria do PC (so troca se ainda estiver no padrao)
    $modelo = Ler-VariavelEnv "OLLAMA_MODEL"
    if (-not $modelo) { $modelo = "llama3.2:3b" }
    if ($modelo -eq "llama3.2:3b") {
        try {
            $gb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
            if ($gb -ge 16) { $modelo = "qwen2.5:7b" }
            Escrever "Memoria do PC: $gb GB -> modelo escolhido: $modelo" "DarkGray"
        } catch { }
    }
    Definir-VariavelEnv "OLLAMA_MODEL" $modelo

    $lista = (cmd /c "ollama list 2>&1" | Out-String)
    if ($lista -notmatch [regex]::Escape($modelo)) {
        Escrever "Baixando o modelo $modelo (so na 1a vez, ~2 a 5 GB, pode demorar)..." "Cyan"
        cmd /c "ollama pull $modelo"
        if ($LASTEXITCODE -ne 0) { Escrever "Falhou ao baixar o modelo. Confira a internet e tente de novo." "Red"; return $false }
    }
    return $true
}

function Configurar-IA([switch]$Inicial) {
    Escrever ""
    Escrever "=== Ativar a IA do atendimento (conversa como uma pessoa) ===" "Yellow"
    if ($Inicial) { Escrever "A IA ainda nao foi configurada. Escolha uma opcao para o bot conversar de verdade:" "Yellow" }
    Escrever "  1 - Claude (melhor qualidade; custa centavos por conversa; precisa de chave)"
    Escrever "  2 - Ollama (GRATUITO, roda no seu PC; instala e baixa tudo sozinho)"
    Escrever "  3 - Desligar a IA (nao recomendado: so respostas por palavra-chave)"
    $op = Read-Host "Digite 1, 2 ou 3"

    if ($op -eq "1") {
        Escrever ""
        Escrever "Crie a chave em https://console.anthropic.com  (menu API Keys; precisa de creditos)." "Cyan"
        Start-Process "https://console.anthropic.com/settings/keys"
        $k = Read-Host "Cole a chave aqui (ela nao aparece na tela)" -AsSecureString
        $txt = SecureString-ParaTexto $k
        if ($txt.Length -lt 20) { Escrever "Chave invalida. Nada foi alterado." "Red"; return }
        New-Item -ItemType Directory -Force -Path (Split-Path $arquivoChaveIA) | Out-Null
        ((ConvertTo-SecureString $txt -AsPlainText -Force) | ConvertFrom-SecureString) | Set-Content -Path $arquivoChaveIA -Encoding ASCII
        Definir-VariavelEnv "IA_PROVIDER" "ANTHROPIC"
        Definir-VariavelEnv "ANTHROPIC_API_KEY" ""
        Definir-VariavelEnv "ANTHROPIC_MODEL" "claude-haiku-4-5-20251001"
        Escrever "Pronto! IA com Claude ativada." "Green"
    }
    elseif ($op -eq "2") {
        if (Garantir-Ollama) {
            Definir-VariavelEnv "IA_PROVIDER" "OLLAMA"
            Escrever "Pronto! IA local (Ollama) ativada." "Green"
        } else { return }
    }
    elseif ($op -eq "3") {
        Definir-VariavelEnv "IA_PROVIDER" ""
        Escrever "IA desligada." "Yellow"
    }
    else { Escrever "Nada foi alterado." "Yellow"; return }
    if (-not $Inicial) { Escrever "Feche a janela 'DeliveryBot - Sistema' e abra 'Iniciar DeliveryBot' de novo." "Yellow" }
}

# ---------------------------------------------------------------------------
Escrever ""
Escrever "=======================================================" "DarkYellow"
Escrever "   DeliveryBot -- iniciando" "Yellow"
Escrever "=======================================================" "DarkYellow"

# 0. Primeira execucao: .env e Python ---------------------------------------
$envPath = Join-Path $pastaProjeto ".env"
if (-not (Test-Path $envPath)) {
    Escrever "Primeira vez por aqui: criando o .env..." "Cyan"
    Copy-Item (Join-Path $pastaProjeto ".env.example") $envPath
}

if ($SoTrocarSenha) {
    if (Definir-SenhaCozinha) {
        Escrever "Senha da cozinha atualizada." "Green"
        Escrever "Feche a janela 'DeliveryBot - Sistema' e abra 'Iniciar DeliveryBot' de novo." "Yellow"
    } else { Escrever "Nada foi alterado." "Yellow" }
    exit 0
}

if ($ConfigurarIA) { Configurar-IA; exit 0 }

$venvPython = Join-Path $pastaProjeto "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Escrever ""
    Escrever "Primeira vez: preparando o Python (demora so agora)..." "Cyan"
    $py = $null
    if (Comando-Existe "python") { $py = "python" } elseif (Comando-Existe "py") { $py = "py" }
    if (-not $py) {
        Escrever "Python nao encontrado. Instale em https://www.python.org/downloads/" "Red"
        Escrever "(marque a caixa 'Add python.exe to PATH') e abra este programa de novo." "Red"
        Start-Process "https://www.python.org/downloads/"
        exit 1
    }
    & $py -m venv venv
    & (Join-Path $pastaProjeto "venv\Scripts\python.exe") -m pip install -r requirements.txt --quiet
    Escrever "Python pronto." "Green"
}

# WhatsApp real: se estava em modo TESTE, passa para WAHA
$whatsappProvider = (Ler-VariavelEnv "WHATSAPP_PROVIDER").ToUpper()
if ($whatsappProvider -eq "" -or $whatsappProvider -eq "TESTE") {
    Definir-VariavelEnv "WHATSAPP_PROVIDER" "WAHA"
    $whatsappProvider = "WAHA"
    Escrever "WhatsApp ajustado para o modo REAL (WAHA)." "Cyan"
}

# Segredos tecnicos (a senha da cozinha NAO entra aqui)
$gerou = $false
foreach ($nomeVar in @("WEBHOOK_SECRET", "WAHA_DASHBOARD_PASSWORD", "WAHA_API_KEY")) {
    if (-not (Ler-VariavelEnv $nomeVar)) { Definir-VariavelEnv $nomeVar (Gerar-Segredo); $gerou = $true }
}
if ($gerou) { Escrever "Segredos de seguranca gerados (nao exibidos)." "Cyan" }

# 1. Senha da cozinha, protegida pelo Windows --------------------------------
$senhaCozinha = Carregar-SenhaCozinha
if (-not $senhaCozinha) {
    Escrever ""
    Escrever "Vai abrir uma janela para voce criar a SENHA DA COZINHA." "Yellow"
    if (-not (Definir-SenhaCozinha)) {
        Escrever "Sem senha o painel da cozinha fica bloqueado. Rode de novo e crie uma." "Red"
    }
    $senhaCozinha = Carregar-SenhaCozinha
}
# Limpa qualquer senha antiga em texto puro que sobrou no .env
if (Ler-VariavelEnv "COZINHA_SENHA") { Definir-VariavelEnv "COZINHA_SENHA" "" }
# Entrega a senha so ao processo do sistema, via variavel de ambiente
if ($senhaCozinha) { $env:COZINHA_SENHA = $senhaCozinha }

# IA: obrigatoria na partida -- se ainda nao esta configurada, configura agora
$iaProvider = (Ler-VariavelEnv "IA_PROVIDER").ToUpper()
if ($iaProvider -notin @("ANTHROPIC", "OLLAMA")) {
    Definir-VariavelEnv "IA_PROVIDER" "OLLAMA"
    $iaProvider = "OLLAMA"
    Escrever "IA ativada no modo gratuito (Ollama). Para trocar, use 'Configurar IA.bat'." "Cyan"
}
# IA: entrega a chave do Claude so ao processo do sistema
if ($iaProvider -eq "ANTHROPIC") {
    $chaveIA = Carregar-ChaveIA
    if ($chaveIA) { $env:ANTHROPIC_API_KEY = $chaveIA }
    else { Escrever "IA (Claude) sem chave. Rode 'Configurar IA.bat'." "Yellow" }
}
elseif ($iaProvider -eq "OLLAMA") {
    if (-not (Garantir-Ollama)) { Escrever "Ollama nao ficou pronto: a IA vai falhar no teste." "Red" }
}

$cozinhaUsuario = Ler-VariavelEnv "COZINHA_USUARIO"; if (-not $cozinhaUsuario) { $cozinhaUsuario = "admin" }
$wahaApiKey = Ler-VariavelEnv "WAHA_API_KEY"

# 2. Docker Desktop + WAHA ---------------------------------------------------
function Docker-Rodando {
    cmd /c "docker info >nul 2>&1"
    return $LASTEXITCODE -eq 0
}

function Garantir-DockerDesktopAberto {
    # Docker recem-instalado pode nao estar no PATH desta janela
    $binDocker = "$env:ProgramFiles\Docker\Docker\resources\bin"
    if ((Test-Path $binDocker) -and ($env:Path -notlike "*$binDocker*")) { $env:Path += ";$binDocker" }

    if (Docker-Rodando) { return $true }

    $exe = @("$env:ProgramFiles\Docker\Docker\Docker Desktop.exe", "$env:LOCALAPPDATA\Docker\Docker Desktop.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) {
        Escrever "Docker Desktop nao esta instalado neste computador." "Red"
        Escrever "Vou abrir a pagina de download. Instale, reinicie o PC e abra este programa de novo." "Red"
        Start-Process "https://www.docker.com/products/docker-desktop/"
        return $false
    }

    Escrever "Abrindo o Docker Desktop (pode levar 1-2 minutos)..." "Yellow"
    Start-Process $exe
    $seg = 0
    while (-not (Docker-Rodando) -and $seg -lt 240) {
        Start-Sleep -Seconds 3; $seg += 3
        if ($seg % 15 -eq 0) { Escrever "  aguardando o Docker ligar... ($seg s)" "DarkGray" }
    }
    if (Docker-Rodando) { Escrever "Docker pronto." "Green"; return $true }

    Escrever "O Docker nao ligou a tempo. Se ele mostrou algum aviso (aceitar termos," "Red"
    Escrever "ativar WSL/virtualizacao), resolva e abra este programa de novo." "Red"
    return $false
}

function Chamar-Waha($metodo, $caminho, $corpo = $null) {
    $h = @{}; if ($wahaApiKey) { $h["X-Api-Key"] = $wahaApiKey }
    $p = @{ Uri = "http://localhost:3000$caminho"; Method = $metodo; Headers = $h; TimeoutSec = 5; ErrorAction = "Stop" }
    if ($corpo) { $p["Body"] = ($corpo | ConvertTo-Json); $p["ContentType"] = "application/json" }
    return Invoke-RestMethod @p
}

$sessaoOk = $false
if ($whatsappProvider -ne "WAHA") {
    Escrever "WHATSAPP_PROVIDER = $whatsappProvider -- pulando Docker/WAHA." "DarkGray"
} elseif (Garantir-DockerDesktopAberto) {
    Escrever ""
    Escrever "=== Ligando o WAHA (na 1a vez baixa ~1 GB, pode demorar) ===" "Cyan"
    cmd /c "docker compose up -d waha 2>&1"
    if ($LASTEXITCODE -ne 0) {
        Escrever "O 'docker compose up' deu erro (veja acima). Sigo sem o WhatsApp." "Red"
    } else {
        Escrever "Esperando o WAHA responder..." "Cyan"
        $pronto = $false
        for ($i = 0; $i -lt 60 -and -not $pronto; $i++) {
            try { Chamar-Waha "GET" "/api/sessions" | Out-Null; $pronto = $true } catch { Start-Sleep -Seconds 2 }
        }
        if (-not $pronto) { Escrever "O WAHA nao respondeu. Confira o Docker Desktop." "Red" }
        else {
            try {
                $s = Chamar-Waha "GET" "/api/sessions/default"
                if ($s.status -eq "WORKING") { $sessaoOk = $true; Escrever "WhatsApp ja estava conectado." "Green" }
                elseif ($s.status -in @("STOPPED", "FAILED")) { Chamar-Waha "POST" "/api/sessions/default/start" | Out-Null }
            } catch {
                try { Chamar-Waha "POST" "/api/sessions" @{ name = "default"; start = $true } | Out-Null } catch { }
            }
        }
    }
}

# 3. ngrok (opcional) --------------------------------------------------------
$ngrokUrl = $null
function Pegar-UrlNgrok {
    try {
        $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2 -ErrorAction Stop
        $https = $t.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
        if ($https) { return $https.public_url }
    } catch { }
    return $null
}

if (-not (Comando-Existe "ngrok")) {
    Escrever ""
    Escrever "ngrok nao encontrado: o link do pedido so funciona dentro da sua rede." "Yellow"
} else {
    $ngrokUrl = Pegar-UrlNgrok
    if (-not $ngrokUrl) {
        Escrever ""
        Escrever "=== Abrindo o ngrok ===" "Cyan"
        Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'DeliveryBot - ngrok'; ngrok http 5000"
        for ($i = 0; $i -lt 20 -and -not $ngrokUrl; $i++) { Start-Sleep -Seconds 1; $ngrokUrl = Pegar-UrlNgrok }
    }
    if ($ngrokUrl) {
        Escrever "Link publico: $ngrokUrl" "Green"
        Definir-VariavelEnv "BASE_URL" $ngrokUrl
    } else {
        Escrever "Nao consegui o link do ngrok. Veja a janela dele (talvez falte o authtoken)." "Red"
    }
}

# 4. Sistema (Flask) ---------------------------------------------------------
Escrever ""
Escrever "=== Ligando o sistema ===" "Cyan"
Start-Process powershell -WorkingDirectory $pastaProjeto -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'DeliveryBot - Sistema'; & '$venvPython' -m src.app"

# Se a porta 5000 ja estiver ocupada por outro programa, o sistema nao sobe.
$donoPorta = $null
try {
    $con = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction Stop | Select-Object -First 1
    if ($con) { $donoPorta = (Get-Process -Id $con.OwningProcess -ErrorAction SilentlyContinue).ProcessName }
} catch { }

$flaskOk = $false
Escrever "Esperando o sistema ligar (na 1a vez pode levar ate 2 minutos)..." "Cyan"
for ($i = 0; $i -lt 60 -and -not $flaskOk; $i++) {
    try { Invoke-WebRequest -Uri "http://127.0.0.1:5000/whatsapp/status" -UseBasicParsing -TimeoutSec 3 | Out-Null; $flaskOk = $true }
    catch { Start-Sleep -Seconds 2 }
    if ($i -gt 0 -and $i % 10 -eq 0 -and -not $flaskOk) { Escrever "  ainda ligando... ($($i * 2)s)" "DarkGray" }
}
if ($flaskOk) { Escrever "Sistema no ar." "Green" }
else {
    Escrever "O sistema nao respondeu em 2 minutos." "Red"
    if ($donoPorta) { Escrever "A porta 5000 ja estava sendo usada pelo programa '$donoPorta'. Feche-o e tente de novo." "Red" }
    Escrever "Veja a janela 'DeliveryBot - Sistema': a ultima mensagem vermelha diz o motivo." "Red"
    Escrever "Mesmo assim, abra http://localhost:5000/whatsapp quando ela mostrar 'Running on'." "Yellow"
    Start-Process "http://localhost:5000/whatsapp"
}

# 4b. Teste real da IA --------------------------------------------------------
$iaFuncionando = $false
if ($iaProvider -in @("ANTHROPIC", "OLLAMA")) {
    Escrever ""
    Escrever "Testando a IA com uma pergunta de verdade..." "Cyan"
    $saida = (& $venvPython testar_ia.py --curto | Out-String).Trim()
    if ($saida -match "IA_OK") {
        $iaFuncionando = $true
        Escrever "IA funcionando! Resposta de teste: $($saida -replace '^IA_OK:\s*', '')" "Green"
    } else {
        Escrever "A IA NAO respondeu: $($saida -replace '^IA_FALHOU:\s*', '')" "Red"
        if ($iaProvider -eq "ANTHROPIC") { Escrever "Confira se a chave esta certa e se a conta tem creditos (console.anthropic.com > Billing). Troque a chave em 'Configurar IA.bat'." "Yellow" }
        else { Escrever "Confira se o Ollama esta aberto e o modelo foi baixado ('Configurar IA.bat')." "Yellow" }
    }
}

# 5. QR Code do WhatsApp -----------------------------------------------------
if ($whatsappProvider -eq "WAHA" -and -not $sessaoOk -and $flaskOk) {
    Escrever ""
    Escrever "Abrindo a pagina para conectar o WhatsApp (QR Code)..." "Yellow"
    Start-Process "http://localhost:5000/whatsapp"
    Escrever "Escaneie o QR Code com o celular do restaurante. Aguardando (ate 5 min)..." "Yellow"
    for ($i = 0; $i -lt 100 -and -not $sessaoOk; $i++) {
        Start-Sleep -Seconds 3
        try { if ((Chamar-Waha "GET" "/api/sessions/default").status -eq "WORKING") { $sessaoOk = $true } } catch { }
    }
    if ($sessaoOk) { Escrever "WhatsApp CONECTADO!" "Green" }
    else { Escrever "Ainda nao conectou. A pagina http://localhost:5000/whatsapp continua valendo." "Yellow" }
}

# 6. Resumo ------------------------------------------------------------------
Escrever ""
Escrever "=======================================================" "DarkYellow"
Escrever "   Tudo pronto!" "Green"
Escrever "=======================================================" "DarkYellow"
$base = if ($ngrokUrl) { $ngrokUrl } else { "http://localhost:5000" }
Escrever "Painel da cozinha: $base/cozinha" "White"
Escrever "Login: usuario '$cozinhaUsuario' + a senha que voce criou na janela do Windows." "White"
Escrever "(Para trocar a senha: 'Trocar senha da cozinha.bat')" "DarkGray"
if ($iaFuncionando) { Escrever "Atendimento com IA: LIGADO e testado ($iaProvider)" "Green" }
elseif ($iaProvider -in @("ANTHROPIC", "OLLAMA")) { Escrever "Atendimento com IA: configurado, mas o teste FALHOU (veja acima)." "Red" }
else { Escrever "Atendimento com IA: DESLIGADO -- de duplo clique em 'Configurar IA.bat' para o bot conversar como uma pessoa." "Yellow" }
Escrever ""
Escrever "Nao feche as janelas 'ngrok' e 'Sistema'. Para parar: 'Parar DeliveryBot.bat'." "DarkGray"
