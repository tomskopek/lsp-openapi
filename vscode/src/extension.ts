import { ExtensionContext, workspace } from 'vscode';
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

export function activate(context: ExtensionContext) {
  const serverPath = context.asAbsolutePath('server.py');
  const python = workspace.getConfiguration('lspOpenapi').get<string>('python', 'python3');

  const serverOptions: ServerOptions = {
    command: python,
    args: [serverPath],
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: 'file', language: 'yaml' }],
  };

  client = new LanguageClient(
    'lspOpenapi',
    'OpenAPI LSP',
    serverOptions,
    clientOptions,
  );

  client.start();
}

export function deactivate(): Thenable<void> | undefined {
  return client?.stop();
}
