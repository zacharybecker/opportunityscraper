import { useState, useRef, useEffect } from 'react'
import {
  Title, Stack, Card, TextInput, Button, Group, Text,
  ScrollArea, Loader, ActionIcon, Paper, NavLink, Center,
} from '@mantine/core'
import { IconSend, IconPlus, IconTrash, IconMessageCircle } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getChatSessions, createChatSession, deleteChatSession } from '../api'
import { useAuthStore } from '../store'
import type { ChatSession, ChatMessage } from '../types'

export default function Chat() {
  const queryClient = useQueryClient()
  const [activeSession, setActiveSession] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const token = useAuthStore((s) => s.token)

  const { data: sessions } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: getChatSessions,
  })

  const createMutation = useMutation({
    mutationFn: createChatSession,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setActiveSession(data.id)
      setMessages([])
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteChatSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      if (activeSession) setActiveSession(null)
      setMessages([])
    },
  })

  useEffect(() => {
    if (activeSession && sessions) {
      const session = sessions.find((s) => s.id === activeSession)
      if (session) setMessages(session.messages || [])
    }
  }, [activeSession, sessions])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, streamingContent])

  const sendMessage = async () => {
    if (!input.trim() || !activeSession || streaming) return

    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg, created_at: new Date().toISOString() }])
    setStreaming(true)
    setStreamingContent('')

    try {
      const response = await fetch(`/api/v1/chat/sessions/${activeSession}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: userMsg }),
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const text = decoder.decode(value)
          const lines = text.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.token) {
                  fullContent += data.token
                  setStreamingContent(fullContent)
                }
                if (data.done) break
              } catch {}
            }
          }
        }
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: fullContent, created_at: new Date().toISOString() },
      ])
      setStreamingContent('')
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error: Failed to get response', created_at: new Date().toISOString() },
      ])
    } finally {
      setStreaming(false)
    }
  }

  return (
    <Stack h="calc(100vh - 140px)">
      <Title order={2}>Chat</Title>

      <div style={{ display: 'flex', gap: 16, flex: 1, minHeight: 0 }}>
        <Card shadow="sm" padding="xs" radius="md" withBorder w={250} style={{ flexShrink: 0 }}>
          <Button fullWidth size="xs" leftSection={<IconPlus size={14} />} mb="xs"
            onClick={() => createMutation.mutate()} loading={createMutation.isPending}
          >
            New Chat
          </Button>
          <ScrollArea h="calc(100vh - 280px)">
            {sessions?.map((session) => (
              <NavLink
                key={session.id}
                label={session.title || 'Chat'}
                description={`${session.messages?.length || 0} messages`}
                leftSection={<IconMessageCircle size={16} />}
                active={activeSession === session.id}
                onClick={() => setActiveSession(session.id)}
                rightSection={
                  <ActionIcon size="xs" variant="subtle" color="red"
                    onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(session.id) }}
                  >
                    <IconTrash size={12} />
                  </ActionIcon>
                }
              />
            ))}
            {!sessions?.length && <Text size="sm" c="dimmed" ta="center" mt="lg">No chat sessions</Text>}
          </ScrollArea>
        </Card>

        <Card shadow="sm" padding="md" radius="md" withBorder style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {activeSession ? (
            <>
              <ScrollArea style={{ flex: 1 }} viewportRef={scrollRef}>
                <Stack gap="sm" p="xs">
                  {messages.map((msg, i) => (
                    <Paper
                      key={i}
                      p="sm"
                      radius="md"
                      bg={msg.role === 'user' ? 'blue.0' : 'gray.0'}
                      style={{ alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%' }}
                    >
                      <Text size="xs" c="dimmed" mb={4}>{msg.role === 'user' ? 'You' : 'Assistant'}</Text>
                      <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Text>
                    </Paper>
                  ))}
                  {streaming && streamingContent && (
                    <Paper p="sm" radius="md" bg="gray.0" style={{ maxWidth: '80%' }}>
                      <Text size="xs" c="dimmed" mb={4}>Assistant</Text>
                      <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>{streamingContent}</Text>
                    </Paper>
                  )}
                  {streaming && !streamingContent && (
                    <Group gap="xs"><Loader size="xs" /><Text size="sm" c="dimmed">Thinking...</Text></Group>
                  )}
                </Stack>
              </ScrollArea>

              <Group mt="md" gap="xs">
                <TextInput
                  placeholder="Ask about opportunities, pipeline, deadlines..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                  style={{ flex: 1 }}
                  disabled={streaming}
                />
                <ActionIcon size="lg" onClick={sendMessage} disabled={streaming || !input.trim()}>
                  <IconSend size={18} />
                </ActionIcon>
              </Group>
            </>
          ) : (
            <Center style={{ flex: 1 }}>
              <Text c="dimmed">Select or create a chat session</Text>
            </Center>
          )}
        </Card>
      </div>
    </Stack>
  )
}
