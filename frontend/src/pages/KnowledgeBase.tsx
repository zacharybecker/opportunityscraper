import { useState } from 'react'
import {
  Title, Stack, Card, Group, Button, Text, Badge, Table,
  Modal, TextInput, Select, Loader, Center, Textarea,
  Tabs, ActionIcon,
} from '@mantine/core'
import { Dropzone, MIME_TYPES } from '@mantine/dropzone'
import { IconUpload, IconFile, IconTrash, IconExternalLink, IconX } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { notifications } from '@mantine/notifications'
import apiClient from '../api/client'

interface KnowledgeDoc {
  id: string
  title: string
  doc_type: string
  original_filename: string | null
  url: string | null
  category: string
  has_text: boolean
  text_length: number
  created_at: string
}

export default function KnowledgeBase() {
  const queryClient = useQueryClient()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [urlOpen, setUrlOpen] = useState(false)
  const [category, setCategory] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [previewDoc, setPreviewDoc] = useState<any>(null)
  const [urlForm, setUrlForm] = useState({ url: '', title: '', category: 'general' })

  const { data, isLoading } = useQuery({
    queryKey: ['knowledge-docs', category, search],
    queryFn: () =>
      apiClient.get('/knowledge/documents', {
        params: { category: category || undefined, search: search || undefined },
      }).then((r) => r.data),
  })

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => {
      const promises = files.map((file) => {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('title', file.name)
        formData.append('category', category || 'general')
        return apiClient.post('/knowledge/documents', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      })
      return Promise.all(promises)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-docs'] })
      setUploadOpen(false)
      notifications.show({ title: 'Uploaded', message: 'Documents uploaded successfully', color: 'green' })
    },
  })

  const urlMutation = useMutation({
    mutationFn: () => apiClient.post('/knowledge/documents/url', urlForm).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-docs'] })
      setUrlOpen(false)
      setUrlForm({ url: '', title: '', category: 'general' })
      notifications.show({ title: 'Added', message: 'URL document added', color: 'green' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/knowledge/documents/${id}`).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['knowledge-docs'] }),
  })

  const viewDoc = async (id: string) => {
    const res = await apiClient.get(`/knowledge/documents/${id}`)
    setPreviewDoc(res.data)
  }

  const categoryColors: Record<string, string> = {
    capability: 'blue',
    past_performance: 'green',
    certification: 'violet',
    general: 'gray',
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Knowledge Base</Title>
        <Group>
          <Button leftSection={<IconExternalLink size={16} />} variant="light" onClick={() => setUrlOpen(true)}>
            Add URL
          </Button>
          <Button leftSection={<IconUpload size={16} />} onClick={() => setUploadOpen(true)}>
            Upload
          </Button>
        </Group>
      </Group>

      <Card shadow="sm" padding="md" radius="md" withBorder>
        <Group>
          <TextInput
            placeholder="Search documents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ flex: 1 }}
          />
          <Select
            placeholder="Category"
            data={[
              { value: 'capability', label: 'Capability' },
              { value: 'past_performance', label: 'Past Performance' },
              { value: 'certification', label: 'Certification' },
              { value: 'general', label: 'General' },
            ]}
            value={category}
            onChange={setCategory}
            clearable
            w={180}
          />
        </Group>
      </Card>

      {isLoading ? (
        <Center h={300}><Loader /></Center>
      ) : (
        <Card shadow="sm" padding={0} radius="md" withBorder>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Title</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Text</Table.Th>
                <Table.Th>Added</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.items?.map((doc: KnowledgeDoc) => (
                <Table.Tr key={doc.id}>
                  <Table.Td>
                    <Text size="sm" lineClamp={1} style={{ cursor: 'pointer' }} onClick={() => viewDoc(doc.id)}>
                      {doc.title}
                    </Text>
                  </Table.Td>
                  <Table.Td><Badge size="sm" variant="light">{doc.doc_type}</Badge></Table.Td>
                  <Table.Td>
                    <Badge size="sm" color={categoryColors[doc.category] || 'gray'}>{doc.category}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">{doc.has_text ? `${Math.round(doc.text_length / 1000)}k chars` : 'None'}</Text>
                  </Table.Td>
                  <Table.Td><Text size="xs">{dayjs(doc.created_at).format('MMM D')}</Text></Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {doc.doc_type !== 'url' && (
                        <Button
                          size="xs" variant="subtle"
                          component="a"
                          href={`/api/v1/knowledge/documents/${doc.id}/download`}
                          target="_blank"
                        >
                          Download
                        </Button>
                      )}
                      <ActionIcon size="sm" variant="subtle" color="red" onClick={() => deleteMutation.mutate(doc.id)}>
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {!data?.items?.length && (
                <Table.Tr>
                  <Table.Td colSpan={6}><Text ta="center" c="dimmed" py="xl">No documents</Text></Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {/* Upload Modal */}
      <Modal opened={uploadOpen} onClose={() => setUploadOpen(false)} title="Upload Documents" size="lg">
        <Stack>
          <Dropzone
            onDrop={(files) => uploadMutation.mutate(files)}
            loading={uploadMutation.isPending}
            accept={[MIME_TYPES.pdf, MIME_TYPES.docx, MIME_TYPES.doc, 'text/plain', 'text/csv']}
            maxSize={50 * 1024 * 1024}
          >
            <Group justify="center" gap="xl" style={{ minHeight: 120, pointerEvents: 'none' }}>
              <Dropzone.Accept><IconUpload size={40} /></Dropzone.Accept>
              <Dropzone.Reject><IconX size={40} /></Dropzone.Reject>
              <Dropzone.Idle><IconFile size={40} /></Dropzone.Idle>
              <div>
                <Text size="lg" inline>Drag files here or click to select</Text>
                <Text size="sm" c="dimmed" inline mt={7}>PDF, DOCX, TXT, CSV - max 50MB</Text>
              </div>
            </Group>
          </Dropzone>
        </Stack>
      </Modal>

      {/* URL Modal */}
      <Modal opened={urlOpen} onClose={() => setUrlOpen(false)} title="Add URL Document">
        <Stack>
          <TextInput label="URL" placeholder="https://..." value={urlForm.url} onChange={(e) => setUrlForm({ ...urlForm, url: e.target.value })} />
          <TextInput label="Title" placeholder="Document title" value={urlForm.title} onChange={(e) => setUrlForm({ ...urlForm, title: e.target.value })} />
          <Select
            label="Category"
            data={['capability', 'past_performance', 'certification', 'general']}
            value={urlForm.category}
            onChange={(v) => setUrlForm({ ...urlForm, category: v || 'general' })}
          />
          <Button onClick={() => urlMutation.mutate()} loading={urlMutation.isPending}>Add</Button>
        </Stack>
      </Modal>

      {/* Preview Modal */}
      <Modal opened={!!previewDoc} onClose={() => setPreviewDoc(null)} title={previewDoc?.title} size="xl">
        {previewDoc && (
          <Stack>
            <Group gap="xs">
              <Badge>{previewDoc.doc_type}</Badge>
              <Badge color={categoryColors[previewDoc.category] || 'gray'}>{previewDoc.category}</Badge>
            </Group>
            {previewDoc.extracted_text ? (
              <Textarea
                value={previewDoc.extracted_text}
                readOnly
                minRows={15}
                maxRows={30}
                autosize
              />
            ) : (
              <Text c="dimmed">No extracted text available</Text>
            )}
          </Stack>
        )}
      </Modal>
    </Stack>
  )
}
