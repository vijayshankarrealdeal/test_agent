
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:gpt_markdown/gpt_markdown.dart';
import 'package:uuid/uuid.dart';

class ChatMessage {
  final String text;
  final bool isUser;

  ChatMessage({required this.text, required this.isUser});
}

class ChatProvider with ChangeNotifier {
  ChatProvider() {
    _sessionId = _uuid.v4();
  }

  final Uuid _uuid = const Uuid();
  final List<ChatMessage> _messages = [];
  final String _chatEndpoint = 'https://test-agent-d0zw.onrender.com/chat';
  late String _sessionId;
  bool _isLoading = false;

  List<ChatMessage> get messages => _messages;
  bool get isLoading => _isLoading;

  Future<void> refreshChat() async {
    _messages.clear();
    _sessionId = _uuid.v4();
    notifyListeners();
  }

  Future<void> sendMessage(String text) async {
    final userMessage = ChatMessage(text: text, isUser: true);
    _messages.add(userMessage);
    _isLoading = true;
    notifyListeners();

    final history = _messages.reversed.take(5).map((m) {
      return (m.isUser ? 'user: ' : 'assistant: ') + m.text;
    }).toList();

    try {
      final response = await http.post(
        Uri.parse(_chatEndpoint),
        headers: {
          'Content-Type': 'application/json',
          'accept': 'application/json'
        },
        body: jsonEncode({
          'query': text,
          'session_id': _sessionId,
          'history': history,
        }),
      );

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        final botMessage = ChatMessage(text: responseData['response'], isUser: false);
        _messages.add(botMessage);
      } else {
        _messages.add(ChatMessage(text: 'Error: Could not connect to the server.', isUser: false));
      }
    } catch (e) {
      _messages.add(ChatMessage(text: 'Error: $e', isUser: false));
    }
    _isLoading = false;
    notifyListeners();
  }
}

class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final chatProvider = Provider.of<ChatProvider>(context);
    final textController = TextEditingController();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Hello'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              chatProvider.refreshChat();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: RefreshIndicator(
              onRefresh: chatProvider.refreshChat,
              child: ListView.builder(
                physics: const AlwaysScrollableScrollPhysics(),
                itemCount: chatProvider.messages.length,
                itemBuilder: (context, index) {
                  final message = chatProvider.messages[index];
                  return ListTile(
                    title: Align(
                      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        padding: const EdgeInsets.all(8.0),
                        decoration: BoxDecoration(
                          color: message.isUser
                              ? Theme.of(context).colorScheme.primary
                              : Theme.of(context).colorScheme.secondary,
                          borderRadius: BorderRadius.circular(8.0),
                        ),
                        child: message.isUser
                            ? Text(
                                message.text,
                                style: TextStyle(
                                  color: message.isUser
                                      ? Theme.of(context).colorScheme.onPrimary
                                      : Theme.of(context).colorScheme.onSecondary,
                                ),
                              )
                            : GptMarkdown(
                                 message.text,
                              ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          if (chatProvider.isLoading)
            const Padding(
              padding: EdgeInsets.only(bottom: 8.0),
              child: SizedBox(
                height: 24,
                width: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: textController,
                    decoration: const InputDecoration(
                      hintText: 'Type a message...',
                    ),
                    enabled: !chatProvider.isLoading,
                    onSubmitted: (text) {
                      if (text.isNotEmpty) {
                        chatProvider.sendMessage(text);
                        textController.clear();
                      }
                    },
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: chatProvider.isLoading
                      ? null
                      : () {
                  final text = textController.text;
                  if (text.isNotEmpty) {
                    chatProvider.sendMessage(text);
                    textController.clear();
                  }
                },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
