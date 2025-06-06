# PowerShellスクリプト - run_dev.ps1
# スクリプトの文字コードをUTF-8に設定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# スクリプトのディレクトリに移動
Set-Location -Path $PSScriptRoot

# 環境変数の初期化
$VENV_PATH = ".\venv"
$DEFAULT_SCRIPT = "src.main"
$APP_ENV = ""
$SCRIPT_TO_RUN = ""
$TEST_MODE = ""

# プロジェクトルートをPYTHONPATHに追加
$env:PYTHONPATH = (Get-Location).Path

# ヘルプメッセージの表示
if ($args -contains "--help") {
    Write-Host "使用方法:"
    Write-Host "  .\run_dev.ps1 [オプション]"
    Write-Host ""
    Write-Host "オプション:"
    Write-Host "  --env [dev|prd] : 実行環境を指定します。"
    Write-Host "                     (dev=development, prd=production)"
    Write-Host "  --help          : このヘルプを表示します。"
    Write-Host ""
    Write-Host "環境モード:"
    Write-Host "  dev  : 開発環境で実行、詳細なログとデバッグ情報を表示"
    Write-Host "  prd  : 本番運用環境、安定性重視でユーザー向け"
    Write-Host ""
    Write-Host "例:"
    Write-Host "  .\run_dev.ps1 --env dev"
    Write-Host "  .\run_dev.ps1 --env prd"
    exit 0
}

# 引数がない場合はユーザーに選択を促す
if ($args.Count -eq 0) {
    Write-Host "実行環境を選択してください:"
    Write-Host "  1. Development (dev)"
    Write-Host "  2. Production (prd)"
    $CHOICE = Read-Host "選択肢を入力してください (1/2)"
    
    $CHOICE = $CHOICE.Trim()
    
    if ($CHOICE -eq "1") {
        $APP_ENV = "development"
        Write-Host "[LOG] 開発環境モードを選択しました。"
    }
    elseif ($CHOICE -eq "2") {
        $APP_ENV = "production"
        Write-Host "[LOG] 本番環境モードを選択しました。"
    }
    else {
        Write-Host "Error: 無効な選択肢です。再実行してください。" -ForegroundColor Red
        exit 1
    }
    
    if (-not $SCRIPT_TO_RUN) {
        $SCRIPT_TO_RUN = $DEFAULT_SCRIPT
    }
}

# Pythonがインストールされているか確認
try {
    $pythonVersion = (python --version 2>&1)
    Write-Host "[LOG] Python バージョン: $pythonVersion"
}
catch {
    Write-Host "Error: Python がインストールされていないか、環境パスが設定されていません。" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 仮想環境がなければ作成
if (-not (Test-Path "$VENV_PATH\Scripts\Activate.ps1")) {
    Write-Host "[LOG] 仮想環境が存在しません。作成中..."
    try {
        python -m venv $VENV_PATH
        Write-Host "[LOG] 仮想環境が正常に作成されました。"
    }
    catch {
        Write-Host "Error: 仮想環境の作成に失敗しました。" -ForegroundColor Red
        Write-Host $_.Exception.Message
        Read-Host "続行するには何かキーを押してください..."
        exit 1
    }
}

# 仮想環境を有効化
try {
    if (Test-Path "$VENV_PATH\Scripts\Activate.ps1") {
        . "$VENV_PATH\Scripts\Activate.ps1"
        Write-Host "[LOG] 仮想環境を有効化しました。"
    }
    else {
        Write-Host "Error: 仮想環境の有効化に失敗しました。Activate.ps1 スクリプトが見つかりません。" -ForegroundColor Red
        Read-Host "続行するには何かキーを押してください..."
        exit 1
    }
}
catch {
    Write-Host "Error: 仮想環境の有効化中にエラーが発生しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# requirements.txtの確認
if (-not (Test-Path "requirements.txt")) {
    Write-Host "Error: requirements.txt が見つかりません。" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 必要に応じてパッケージをインストール
try {
    $CurrentHash = (Get-FileHash -Path "requirements.txt" -Algorithm SHA256).Hash
    $StoredHash = ""
    if (Test-Path ".req_hash") {
        $StoredHash = Get-Content ".req_hash"
    }

    if ($CurrentHash -ne $StoredHash) {
        Write-Host "[LOG] 必要なパッケージをインストール中..."
        try {
            # 現在のプロジェクトの仮想環境を確実に使用
            & "$VENV_PATH\Scripts\python.exe" -m pip install -r requirements.txt
            $CurrentHash | Out-File -FilePath ".req_hash"
            Write-Host "[LOG] パッケージのインストールが完了しました。"
        }
        catch {
            Write-Host "Error: パッケージのインストールに失敗しました。" -ForegroundColor Red
            Write-Host $_.Exception.Message
            Read-Host "続行するには何かキーを押してください..."
            exit 1
        }
    }
    else {
        Write-Host "[LOG] パッケージは最新です。インストールをスキップします。"
    }
}
catch {
    Write-Host "Error: ハッシュ計算に失敗しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# スクリプトを実行
Write-Host "[LOG] 環境: $APP_ENV"
Write-Host "[LOG] 実行スクリプト: $SCRIPT_TO_RUN"
try {
    if ($SCRIPT_TO_RUN) {
        python -m $SCRIPT_TO_RUN --env $APP_ENV $TEST_MODE
        Write-Host "[LOG] スクリプトが正常に実行されました。"
    }
    else {
        Write-Host "Error: 実行するスクリプトが指定されていません。" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "Error: スクリプトの実行に失敗しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}
