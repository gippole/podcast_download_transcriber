import feedparser
import requests
import os
from pathlib import Path
from urllib.parse import urlparse
import time
import re
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

console = Console()

class RSSMp3Downloader:
    def __init__(self, download_folder="downloads"):
        """初期化"""
        self.base_download_folder = download_folder
        self.download_folder = download_folder
        self.downloaded_files = []
        self.mp3_list = []
        self.channel_title = None
        
        # ダウンロードフォルダを作成
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)

    def get_download_folder(self):
        """ダウンロードフォルダのパスを取得"""
        return self.download_folder
    
    def get_downloaded_files(self):
        """ダウンロード済みファイルのリストを取得"""
        return self.downloaded_files
    
    def fetch_rss(self, rss_url):
        """RSSフィードを取得してMP3ファイルのURLを抽出"""
        console.print(f"\n[bold cyan]RSSフィードを取得中...[/bold cyan]: {rss_url}")
        with console.status("[bold green]フィードを解析中...[/bold green]", spinner="dots"):
            feed = feedparser.parse(rss_url)
        
        # チャンネルタイトルを取得してフォルダ名に設定
        self.channel_title = feed.feed.get('title', 'Unknown Channel')
        sanitized_title = self._sanitize_filename(self.channel_title)
        self.download_folder = os.path.join(self.base_download_folder, sanitized_title)
        
        # 新しいダウンロードフォルダを作成
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]ダウンロード先設定:[/green] {self.download_folder}")
        
        self.mp3_list = []
        
        for entry in feed.entries:
            title = entry.get('title', 'No Title')
            
            # enclosuresからMP3を探す
            if hasattr(entry, 'enclosures'):
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('audio') or enclosure.get('href', '').endswith('.mp3'):
                        # Use enclosure's title if present; otherwise fall back to entry title
                        enclosure_title = enclosure.get('title') or title
                        self.mp3_list.append({
                            'title': title,
                            'enclosure_title': enclosure_title,
                            'url': enclosure.get('href'),
                            'published': entry.get('published', 'Unknown'),
                            'artist': entry.get('author') or entry.get('itunes_author'),
                            'year': entry.get('published_parsed').tm_year if entry.get('published_parsed') else None,
                            'genre': entry.get('tags')[0]['term'] if entry.get('tags') else None
                        })
            
            # linksからMP3を探す
            elif hasattr(entry, 'links'):
                for link in entry.links:
                    if link.get('href', '').endswith('.mp3'):
                        # No enclosure title available in links; use entry title as enclosure_title
                        self.mp3_list.append({
                            'title': title,
                            'enclosure_title': title,
                            'url': link.get('href'),
                            'published': entry.get('published', 'Unknown'),
                            'artist': entry.get('author') or entry.get('itunes_author'),
                            'year': entry.get('published_parsed').tm_year if entry.get('published_parsed') else None,
                            'genre': entry.get('tags')[0]['term'] if entry.get('tags') else None
                        })
        
        console.print(f"[bold green]MP3ファイルを {len(self.mp3_list)} 個見つけました![/bold green]")
        return len(self.mp3_list)
    
    def display_list(self):
        """ダウンロード可能なファイルのリストを表示"""
        if not self.mp3_list:
            console.print("[bold red]ファイルがありません。先にRSSフィードを取得してください。[/bold red]")
            return
        
        table = Table(title=f"ダウンロード可能なMP3ファイル一覧\nチャンネル: {self.channel_title or 'Unknown'}")
        
        table.add_column("No.", justify="right", style="cyan", no_wrap=True)
        table.add_column("タイトル", style="magenta")
        table.add_column("状態", justify="center")
        table.add_column("公開日", justify="right", style="green")

        for idx, item in enumerate(self.mp3_list, 1):
            filename = self._get_filename(item['url'], item['title'])
            exists = "[green]✓済[/green]" if self._file_exists(filename) else "[yellow]未[/yellow]"
            table.add_row(str(idx), item['title'], exists, item['published'])
            
        console.print(table)
    
    def _sanitize_filename(self, filename):
        """ファイル名から使用できない文字を削除して安全にする"""
        # Windows, Mac, Linuxで使用できない文字を定義
        # Windows: < > : " | ? * \ /
        # Mac/Linux: / (その他の文字は基本的に使用可能だが、統一性のためWindowsに合わせる)
        # 制御文字 (0-31, 127) も削除
        invalid_chars = r'[<>:"|?*\\/\x00-\x1f\x7f]'
        
        # 無効な文字を削除
        sanitized = re.sub(invalid_chars, '', filename)
        
        # Windowsで予約されている名前をチェック
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        # ファイル名の本体部分（拡張子を除く）を取得
        name, ext = os.path.splitext(sanitized)
        
        # 予約名の場合は先頭に"_"を追加
        if name.upper() in reserved_names:
            name = '_' + name
        
        # 先頭と末尾の空白・ピリオドを削除（Windowsでは問題となる）
        name = name.strip(' .')
        
        # 空文字列の場合はデフォルト名を使用
        if not name:
            name = 'untitled'
        
        # ファイル名を再構築
        result = name + ext
        
        # 最大長制限（255文字）
        if len(result) > 255:
            # 拡張子を保持しつつ、名前部分を短縮
            max_name_length = 255 - len(ext)
            result = name[:max_name_length] + ext
        
        return result

    def _get_filename(self, url, title=None):
        """URLからファイル名を取得"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        
        # URLからファイル名が取得できない場合や意味のない場合はタイトルを使用
        name, _ = os.path.splitext(filename)
        if not filename or not name or name in ['', 'index', 'download', 'default', 'file', 'index', 'audio']:
            if title:
                filename = title + '.mp3'
            else:
                filename = 'untitled.mp3'
        elif not filename.endswith('.mp3'):
            filename += '.mp3'
        
        # ファイル名を安全にする
        filename = self._sanitize_filename(filename)
        
        return filename
    
    def _file_exists(self, filename):
        """ファイルが既に存在するかチェック"""
        filepath = os.path.join(self.download_folder, filename)
        return os.path.exists(filepath)
    
    def download_file(self, index):
        """指定されたインデックスのファイルをダウンロード"""
        if index < 1 or index > len(self.mp3_list):
            console.print(f"[bold red]エラー: インデックス {index} は範囲外です。[/bold red]")
            return False
        
        item = self.mp3_list[index - 1]
        url = item['url']
        title = item['title']
        filename = self._get_filename(url, title)
        filepath = os.path.join(self.download_folder, filename)
        
        # 既にファイルが存在する場合はスキップ
        if self._file_exists(filename):
            console.print(f"[yellow]スキップ:[/yellow] {filename} は既に存在します。")
            return True
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]ダウンロード中: {filename}[/cyan]", total=total_size)
                
                with open(filepath, 'wb') as f:
                    if total_size == 0:
                        f.write(response.content)
                        progress.update(task, completed=100) # Fake completion for unknown size
                    else:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                progress.update(task, advance=len(chunk))
            
            console.print(f"[bold green]完了:[/bold green] {filename} を保存しました。")
            
            # ダウンロード済みリストに追加
            if filepath not in self.downloaded_files:
                self.downloaded_files.append(filepath)
            
            # Try to write ID3 tags: Title = enclosure_title, Album = channel title
            try:
                enclosure_title = item.get('enclosure_title') or title
                channel_title = self.channel_title or ''
                artist = item.get('artist')
                year = str(item.get('year')) if item.get('year') else None
                genre = item.get('genre')
                self._write_id3_tags(filepath, title=enclosure_title, album=channel_title, artist=artist, year=year, genre=genre)
            except Exception as e:
                console.print(f"[yellow]警告: ID3タグの書き込みに失敗しました。({e})[/yellow]")
            return True
            
        except Exception as e:
            console.print(f"\n[bold red]エラー:[/bold red] {filename} のダウンロードに失敗しました。({e})")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False

    def _write_id3_tags(self, filepath, title=None, album=None, artist=None, year=None, genre=None):
        """MP3ファイルにID3タグを書き込む。mutagenが無ければ何もしない。既存のタグは上書きしない。"""
        try:
            from mutagen.easyid3 import EasyID3
            from mutagen.id3 import ID3NoHeaderError
        except Exception:
            # mutagenが利用できない場合はスキップ
            console.print("[yellow]mutagenが見つかりません。ID3タグの書き込みをスキップします。\nrequirements.txtを参照して 'mutagen' をインストールしてください。[/yellow]")
            return

        try:
            try:
                tags = EasyID3(filepath)
            except ID3NoHeaderError:
                # ファイルにID3ヘッダがない場合、新しく作成
                tags = EasyID3()

            # 基本的に空の場合のみ書き込む
            if title and not tags.get('title'):
                tags['title'] = title
            if album and not tags.get('album'):
                tags['album'] = album
            if artist and not tags.get('artist'):
                tags['artist'] = artist
            if year and not tags.get('date'):
                tags['date'] = year
            if genre and not tags.get('genre'):
                tags['genre'] = genre

            tags.save(filepath)
            console.print(f"[dim]ID3タグを確認/更新しました: Title='{tags.get('title', [''])[0]}', Album='{tags.get('album', [''])[0]}'[/dim]")
        except Exception as e:
            console.print(f"[bold red]エラー: タグ書き込み失敗[/bold red] {e}")
            raise
    
    def download_range(self, start, end):
        """指定された範囲のファイルをダウンロード"""
        if start < 1 or end > len(self.mp3_list) or start > end:
            console.print(f"[bold red]エラー: 範囲指定が不正です。1から{len(self.mp3_list)}の範囲で指定してください。[/bold red]")
            return
        
        console.print(f"\n[bold cyan]{start}番から{end}番までをダウンロードします。[/bold cyan]")
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for i in range(start, end + 1):
            item = self.mp3_list[i - 1]
            filename = self._get_filename(item['url'], item['title'])
            
            if self._file_exists(filename):
                skip_count += 1
                console.print(f"[yellow]スキップ:[/yellow] {filename} は既に存在します。")
                continue
            
            if self.download_file(i):
                success_count += 1
            else:
                fail_count += 1
            
            # 連続ダウンロード時は少し待機
            if i < end:
                time.sleep(0.5)
        
        console.print(f"\n[bold green]完了: {success_count}個ダウンロード, {skip_count}個スキップ, {fail_count}個失敗[/bold green]")
