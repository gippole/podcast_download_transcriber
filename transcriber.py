import sys
import os
import whisper
import warnings
from rich.console import Console

class Transcriber:
    # Suppress FP16 warning on CPU
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

    SUPPORTED_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.mp4')

    def __init__(self, model_name="base"):
        self.console = Console()
        self.console.print(f"[bold cyan]Loading model '{model_name}'...[/bold cyan]")
        
        try:
            with self.console.status("[bold green]Loading Whisper model...[/bold green]", spinner="dots"):
                self.model = whisper.load_model(model_name)
        except Exception as e:
            self.console.print(f"[bold red]Error loading model: {e}[/bold red]")
            sys.exit(1)


    def transcribe_file(self, model, file_path):
        """
        Helper function to transcribe a single file using a loaded model.
        """

        if not file_path:
            return
        
        base_name = os.path.splitext(file_path)[0]
        output_file = f"{base_name}.txt"

        if os.path.exists(output_file):
            self.console.print(f"[bold yellow]スキップ: [/bold yellow] '{output_file}' は既に存在します")
            return

        self.console.print(f"[cyan]Processing:[/cyan] {file_path}")
        try:
            with self.console.status(f"[bold yellow]Transcribing {os.path.basename(file_path)}...[/bold yellow]", spinner="dots"):
                result = model.transcribe(file_path)
        except Exception as e:
            self.console.print(f"[bold red]Error transcribing '{file_path}': {e}[/bold red]")
            return

        output_text = result["text"]

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output_text.strip())
            self.console.print(f"[bold green]Saved:[/bold green] {output_file}")
        except Exception as e:
            self.console.print(f"[bold red]Error saving output for '{file_path}': {e}[/bold red]")

    def process_directory(self, directory_path):
        """
        Scan directory for audio files and transcribe them.
        """
        if not os.path.exists(directory_path):
            self.console.print(f"[bold red]Error: Directory '{directory_path}' not found.[/bold red]")
            sys.exit(1)

        # Find audio files
        audio_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(self.SUPPORTED_EXTENSIONS):
                    audio_files.append(os.path.join(root, file))

        if not audio_files:
            self.console.print(f"[yellow]No audio files found in '{directory_path}' with extensions {self.SUPPORTED_EXTENSIONS}[/yellow]")
            return

        self.console.print(f"[green]Found {len(audio_files)} audio files.[/green]")

        self.process_files(audio_files)
        
    def process_files(self, audio_files):
        """
        Process a list of audio files.
        """
        if not audio_files:
            self.console.print("[bold red]No audio files provided.[/bold red]")
            return
        
        for i, file_path in enumerate(audio_files, 1):
            self.console.print(f"[bold magenta][{i}/{len(audio_files)}][/bold magenta] Starting transcription...")
            self.transcribe_file(self.model, file_path)
        
        self.console.print("[bold blue]Batch processing complete![/bold blue]")

if __name__ == "__main__":
    # 引数からファイルパスを受け取る
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        transcriber = Transcriber()
        transcriber.transcribe_file(transcriber.model, file_path)