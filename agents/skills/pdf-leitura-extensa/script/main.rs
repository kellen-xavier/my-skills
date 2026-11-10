//! CLI isolada para leitura de PDFs extensos.
mod common;
mod commands {
    pub mod extract_text;
    pub mod inventory;
    pub mod rasterize;
    pub mod read_large;
}

use std::env;

fn print_help() {
    println!(
        "Uso: pdf_toolkit <comando> [opcoes]\n\n\
         Comandos de leitura extensa:\n\
         \x20 inventory     Inspeciona a estrutura e a camada de texto do PDF\n\
         \x20 read-large    Divide PDF extenso em blocos com âncoras de página\n\
         \x20 extract-text  Extrai texto de PDFs menores\n\
         \x20 rasterize     Converte páginas escaneadas em imagens para OCR\n\n\
         Use 'pdf_toolkit <comando> --help' para detalhes."
    );
}

fn main() {
    let argv: Vec<String> = env::args().collect();
    let args = &argv[1..];
    let Some(subcommand) = args.first() else {
        print_help();
        std::process::exit(1);
    };
    let rest = &args[1..];
    let code = match subcommand.as_str() {
        "inventory" => commands::inventory::run_cmd(rest),
        "read-large" => commands::read_large::run_cmd(rest),
        "extract-text" => commands::extract_text::run_cmd(rest),
        "rasterize" => commands::rasterize::run_cmd(rest),
        "--help" | "-h" | "help" => {
            print_help();
            0
        }
        other => {
            eprintln!("Comando desconhecido: {other}\n");
            print_help();
            2
        }
    };
    std::process::exit(code);
}
