import { useState, useCallback } from 'react'
import {
  Title, Stack, Card, Group, Button, Text, Badge, Select,
  Loader, Center, Textarea, TextInput, Drawer, ActionIcon,
  Divider, Paper,
} from '@mantine/core'
import {
  IconDeviceFloppy, IconSparkles, IconArrowLeft,
  IconMessageCircle, IconHistory,
} from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Highlight from '@tiptap/extension-highlight'
import Placeholder from '@tiptap/extension-placeholder'
import TextAlign from '@tiptap/extension-text-align'
import dayjs from 'dayjs'
import { notifications } from '@mantine/notifications'
import apiClient from '../api/client'

export default function ProposalEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [aiDrawer, setAiDrawer] = useState(false)
  const [commentsDrawer, setCommentsDrawer] = useState(false)
  const [aiAction, setAiAction] = useState<string>('rewrite')
  const [aiInstruction, setAiInstruction] = useState('')
  const [aiResult, setAiResult] = useState('')
  const [selectedText, setSelectedText] = useState('')
  const [newComment, setNewComment] = useState('')
  const [sectionTitle, setSectionTitle] = useState('')
  const [sectionDesc, setSectionDesc] = useState('')

  const { data: proposal, isLoading } = useQuery({
    queryKey: ['proposal', id],
    queryFn: () => apiClient.get(`/proposals/${id}`).then((r) => r.data),
    enabled: !!id,
  })

  const latestVersion = proposal?.versions?.[0]

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Highlight,
      Placeholder.configure({ placeholder: 'Start writing your proposal...' }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
    ],
    content: latestVersion?.content || { type: 'doc', content: [{ type: 'paragraph' }] },
    onSelectionUpdate: ({ editor }) => {
      const { from, to } = editor.state.selection
      if (from !== to) {
        setSelectedText(editor.state.doc.textBetween(from, to, ' '))
      }
    },
  }, [latestVersion?.id])

  const saveMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/proposals/${id}/versions`, {
        content: editor?.getJSON(),
        sections: [],
        change_summary: 'Manual save',
      }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proposal', id] })
      notifications.show({ title: 'Saved', message: 'Version saved', color: 'green' })
    },
  })

  const aiMutation = useMutation({
    mutationFn: async () => {
      const text = selectedText || editor?.getText() || ''
      let endpoint = ''
      let body: any = {}

      switch (aiAction) {
        case 'rewrite':
          endpoint = `/proposals/${id}/ai/rewrite`
          body = { text, instruction: aiInstruction || 'Improve clarity and professionalism' }
          break
        case 'expand':
          endpoint = `/proposals/${id}/ai/expand`
          body = { text }
          break
        case 'compliance':
          endpoint = `/proposals/${id}/ai/compliance`
          body = { text }
          break
        case 'generate':
          endpoint = `/proposals/${id}/ai/generate-section`
          body = { section_title: sectionTitle, section_description: sectionDesc }
          break
      }
      return apiClient.post(endpoint, body).then((r) => r.data)
    },
    onSuccess: (data) => {
      setAiResult(data.content)
    },
  })

  const commentMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/proposals/${id}/comments`, { content: newComment }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proposal', id] })
      setNewComment('')
    },
  })

  const acceptAiResult = useCallback(() => {
    if (editor && aiResult) {
      const { from, to } = editor.state.selection
      if (from !== to) {
        editor.chain().focus().deleteRange({ from, to }).insertContent(aiResult).run()
      } else {
        editor.chain().focus().insertContent(aiResult).run()
      }
      setAiResult('')
      setAiDrawer(false)
    }
  }, [editor, aiResult])

  if (isLoading) return <Center h={400}><Loader /></Center>
  if (!proposal) return <Text>Proposal not found</Text>

  const statusColors: Record<string, string> = {
    draft: 'gray', review: 'yellow', submitted: 'blue', final: 'green',
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Group>
          <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={() => navigate('/proposals')}>
            Back
          </Button>
          <Title order={3}>{proposal.title}</Title>
          <Badge color={statusColors[proposal.status]}>{proposal.status}</Badge>
        </Group>
        <Group>
          <Button variant="light" leftSection={<IconHistory size={16} />} onClick={() => setCommentsDrawer(true)}>
            Comments
          </Button>
          <Button variant="light" leftSection={<IconSparkles size={16} />} onClick={() => setAiDrawer(true)} color="violet">
            AI Assist
          </Button>
          <Button leftSection={<IconDeviceFloppy size={16} />} onClick={() => saveMutation.mutate()} loading={saveMutation.isPending}>
            Save
          </Button>
        </Group>
      </Group>

      {/* Editor Toolbar */}
      {editor && (
        <Card shadow="sm" padding="xs" radius="md" withBorder>
          <Group gap="xs">
            <Button size="xs" variant={editor.isActive('bold') ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleBold().run()}>B</Button>
            <Button size="xs" variant={editor.isActive('italic') ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleItalic().run()}>I</Button>
            <Button size="xs" variant={editor.isActive('underline') ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleUnderline().run()}>U</Button>
            <Divider orientation="vertical" />
            <Button size="xs" variant={editor.isActive('heading', { level: 1 }) ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}>H1</Button>
            <Button size="xs" variant={editor.isActive('heading', { level: 2 }) ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>H2</Button>
            <Button size="xs" variant={editor.isActive('heading', { level: 3 }) ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}>H3</Button>
            <Divider orientation="vertical" />
            <Button size="xs" variant={editor.isActive('bulletList') ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleBulletList().run()}>List</Button>
            <Button size="xs" variant={editor.isActive('orderedList') ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleOrderedList().run()}>Ordered</Button>
            <Button size="xs" variant={editor.isActive('blockquote') ? 'filled' : 'light'} onClick={() => editor.chain().focus().toggleBlockquote().run()}>Quote</Button>
          </Group>
        </Card>
      )}

      {/* Editor */}
      <Card shadow="sm" padding="lg" radius="md" withBorder style={{ minHeight: 500 }}>
        <EditorContent editor={editor} style={{ minHeight: 450 }} />
      </Card>

      {/* Version info */}
      <Text size="xs" c="dimmed">
        Version {latestVersion?.version_number || 1} | Last saved {latestVersion?.created_at ? dayjs(latestVersion.created_at).fromNow() : 'never'}
      </Text>

      {/* AI Drawer */}
      <Drawer opened={aiDrawer} onClose={() => setAiDrawer(false)} title="AI Assistant" position="right" size="md">
        <Stack>
          <Select
            label="Action"
            data={[
              { value: 'rewrite', label: 'Rewrite Selected Text' },
              { value: 'expand', label: 'Expand Selected Text' },
              { value: 'compliance', label: 'Add Compliance Language' },
              { value: 'generate', label: 'Generate Section' },
            ]}
            value={aiAction}
            onChange={(v) => setAiAction(v || 'rewrite')}
          />

          {aiAction === 'rewrite' && (
            <TextInput
              label="Instructions"
              placeholder="e.g., Make more concise, improve tone..."
              value={aiInstruction}
              onChange={(e) => setAiInstruction(e.target.value)}
            />
          )}

          {aiAction === 'generate' && (
            <>
              <TextInput label="Section Title" value={sectionTitle} onChange={(e) => setSectionTitle(e.target.value)} />
              <Textarea label="Section Description" value={sectionDesc} onChange={(e) => setSectionDesc(e.target.value)} minRows={2} />
            </>
          )}

          {selectedText && aiAction !== 'generate' && (
            <Paper p="sm" bg="gray.0" radius="md">
              <Text size="xs" c="dimmed" mb={4}>Selected text:</Text>
              <Text size="sm" lineClamp={5}>{selectedText}</Text>
            </Paper>
          )}

          <Button onClick={() => aiMutation.mutate()} loading={aiMutation.isPending} leftSection={<IconSparkles size={16} />} color="violet">
            Generate
          </Button>

          {aiResult && (
            <>
              <Divider label="Result" />
              <Paper p="sm" bg="blue.0" radius="md">
                <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>{aiResult}</Text>
              </Paper>
              <Group>
                <Button onClick={acceptAiResult} color="green">Accept & Insert</Button>
                <Button variant="subtle" onClick={() => setAiResult('')}>Dismiss</Button>
              </Group>
            </>
          )}
        </Stack>
      </Drawer>

      {/* Comments Drawer */}
      <Drawer opened={commentsDrawer} onClose={() => setCommentsDrawer(false)} title="Comments" position="right" size="md">
        <Stack>
          <Group>
            <Textarea
              placeholder="Add a comment..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              style={{ flex: 1 }}
              minRows={2}
            />
          </Group>
          <Button onClick={() => commentMutation.mutate()} loading={commentMutation.isPending} disabled={!newComment.trim()}>
            Add Comment
          </Button>
          <Divider />
          {proposal.comments?.map((c: any) => (
            <Paper key={c.id} p="sm" radius="md" bg={c.resolved ? 'gray.0' : 'yellow.0'}>
              <Text size="xs" c="dimmed">{dayjs(c.created_at).fromNow()}</Text>
              <Text size="sm">{c.content}</Text>
            </Paper>
          ))}
          {!proposal.comments?.length && <Text size="sm" c="dimmed">No comments yet</Text>}
        </Stack>
      </Drawer>
    </Stack>
  )
}
