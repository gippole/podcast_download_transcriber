import os
from rich.console import Console
from rich.panel import Panel
from rss_mp3_downloader import RSSMp3Downloader
from transcriber import Transcriber
import argparse

console = Console()

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Transcribe all audio files in a directory using Whisper.")
    parser.add_argument("--model", default="base", help="Whisper model to use (tiny, base, small, medium, large)")
    args = parser.parse_args()

    downloader = RSSMp3Downloader("downloads")
    myTranscriber = None
    
    console.print(Panel.fit("[bold blue]RSS MP3ダウンローダー[/bold blue]", border_style="blue"))
    
    while True:
        console.print("\n[bold]メニュー[/bold]")
        console.print("1. [cyan]RSSフィードを取得[/cyan]")
        console.print("2. [cyan]ファイル一覧を表示[/cyan]")
        console.print("3. [cyan]ファイルをダウンロード(単一)[/cyan]")
        console.print("4. [cyan]ファイルをダウンロード(範囲指定)[/cyan]")
        console.print("5. [cyan]文字起こし実行[/cyan]")
        console.print("6. [red]終了[/red]")
        
        choice = console.input("\n[bold yellow]選択してください (1-5): [/bold yellow]").strip()
        
        if choice == '1':
            rss_url = console.input("[bold]RSSフィードのURLを入力してください: [/bold]").strip()
            if rss_url:
                downloader.fetch_rss(rss_url)
            else:
                console.print("[red]URLが入力されていません。[/red]")
        
        elif choice == '2':
            downloader.display_list()
        
        elif choice == '3':
            if not downloader.mp3_list:
                console.print("[red]先にRSSフィードを取得してください。[/red]")
                continue
            
            try:
                index = int(console.input(f"ダウンロードするファイルの番号を入力 (1-{len(downloader.mp3_list)}): "))
                downloader.download_file(index)
            except ValueError:
                console.print("[red]エラー: 数値を入力してください。[/red]")
        
        elif choice == '4':
            if not downloader.mp3_list:
                console.print("[red]先にRSSフィードを取得してください。[/red]")
                continue
            
            try:
                start = int(console.input(f"開始番号を入力 (1-{len(downloader.mp3_list)}): "))
                end = int(console.input(f"終了番号を入力 ({start}-{len(downloader.mp3_list)}): "))
                downloader.download_range(start, end)
            except ValueError:
                console.print("[red]エラー: 数値を入力してください。[/red]")
        
        elif choice == '5':
            download_folder = downloader.get_download_folder()

            if not os.path.exists(download_folder):
                console.print(f"[red]エラー: ダウンロード先が空です |{download_folder}|[/red]")

            if not myTranscriber:
                myTranscriber = Transcriber(args.model)
            
            myTranscriber.process_directory(download_folder)
        
        elif choice == '6':
            console.print("[bold blue]終了します。[/bold blue]")
            break
        
        else:
            console.print("[red]エラー: 1-5の数値を入力してください。[/red]")


if __name__ == "__main__":
    main()
