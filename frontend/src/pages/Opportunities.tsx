import { useState } from 'react'
import {
  Title, Stack, TextInput, Group, Select, Table, Badge, Pagination,
  Card, Loader, Center, Text, ActionIcon, Button, Modal, Tabs,
  Textarea,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { Dropzone, MIME_TYPES } from '@mantine/dropzone'
import { IconSearch, IconFilter, IconPlus, IconUpload, IconFile } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { getOpportunities } from '../api'
import apiClient from '../api/client'
import { notifications } from '@mantine/notifications'

export default function Opportunities() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [source, setSource] = useState<string | null>(null)
  const [sortBy] = useState('posted_date')
  const [addOpen, setAddOpen] = useState(false)
  const [pasteText, setPasteText] = useState('')

  const manualForm = useForm({
    initialValues: {
      title: '', description: '', agency: '', solicitation_number: '',
      naics_code: '', set_aside_type: '', response_deadline: '',
      contact_name: '', contact_email: '',
    },
  })

  const manualMutation = useMutation({
    mutationFn: (values: any) => apiClient.post('/opportunities/manual', values).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      setAddOpen(false)
      manualForm.reset()
      notifications.show({ title: 'Created', message: 'Opportunity created', color: 'green' })
      navigate(`/opportunities/${data.id}`)
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => {
      const formData = new FormData()
      formData.append('file', files[0])
      return apiClient.post('/opportunities/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => r.data)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      setAddOpen(false)
      notifications.show({ title: 'Created', message: 'Opportunity extracted and created', color: 'green' })
      navigate(`/opportunities/${data.id}`)
    },
  })

  const pasteMutation = useMutation({
    mutationFn: (text: string) =>
      apiClient.post('/opportunities/manual', {
        title: text.slice(0, 100),
        description: text,
      }).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      setAddOpen(false)
      setPasteText('')
      navigate(`/opportunities/${data.id}`)
    },
  })

  const { data, isLoading } = useQuery({
    queryKey: ['opportunities', { page, search, source, sortBy }],
    queryFn: () => getOpportunities({
      page,
      page_size: 25,
      search: search || undefined,
      source: source || undefined,
      sort_by: sortBy,
      sort_dir: 'desc',
    }),
  })

  const relevancyColor = (score: number | null | undefined) => {
    if (!score) return 'gray'
    if (score >= 80) return 'green'
    if (score >= 50) return 'yellow'
    if (score >= 20) return 'orange'
    return 'red'
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Opportunities</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setAddOpen(true)}>
          Add Opportunity
        </Button>
      </Group>

      <Card shadow="sm" padding="md" radius="md" withBorder>
        <Group>
          <TextInput
            placeholder="Search opportunities..."
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            style={{ flex: 1 }}
          />
          <Select
            placeholder="Source"
            data={[
              { value: 'sam_gov', label: 'SAM.gov' },
              { value: 'generic_web', label: 'Web Portal' },
            ]}
            value={source}
            onChange={(v) => { setSource(v); setPage(1) }}
            clearable
            w={150}
          />
        </Group>
      </Card>

      {isLoading ? (
        <Center h={300}><Loader /></Center>
      ) : (
        <>
          <Card shadow="sm" padding={0} radius="md" withBorder>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Title</Table.Th>
                  <Table.Th>Agency</Table.Th>
                  <Table.Th>Relevancy</Table.Th>
                  <Table.Th>Set-Aside</Table.Th>
                  <Table.Th>Deadline</Table.Th>
                  <Table.Th>Source</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data?.items?.map((opp: any) => (
                  <Table.Tr
                    key={opp.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/opportunities/${opp.id}`)}
                  >
                    <Table.Td maw={300}>
                      <Text size="sm" lineClamp={2}>{opp.title}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" lineClamp={1}>{opp.agency || '-'}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge color={relevancyColor(opp.analysis?.relevancy_score)}>
                        {opp.analysis?.relevancy_score ?? 'N/A'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{opp.set_aside_type || '-'}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {opp.response_deadline ? dayjs(opp.response_deadline).format('MMM D, YYYY') : '-'}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="light" size="sm">
                        {opp.source === 'sam_gov' ? 'SAM.gov' : opp.source}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
                {!data?.items?.length && (
                  <Table.Tr>
                    <Table.Td colSpan={6}>
                      <Text ta="center" c="dimmed" py="xl">No opportunities found</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>

          {data && data.pages > 1 && (
            <Group justify="center">
              <Pagination total={data.pages} value={page} onChange={setPage} />
            </Group>
          )}

          <Text size="sm" c="dimmed" ta="center">
            {data?.total || 0} total opportunities
          </Text>
        </>
      )}

      <Modal opened={addOpen} onClose={() => setAddOpen(false)} title="Add Opportunity" size="lg">
        <Tabs defaultValue="manual">
          <Tabs.List>
            <Tabs.Tab value="manual">Manual Entry</Tabs.Tab>
            <Tabs.Tab value="upload">Upload Document</Tabs.Tab>
            <Tabs.Tab value="paste">Paste Text</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="manual" pt="md">
            <form onSubmit={manualForm.onSubmit((v) => manualMutation.mutate(v))}>
              <Stack>
                <TextInput label="Title" required {...manualForm.getInputProps('title')} />
                <Textarea label="Description" minRows={3} {...manualForm.getInputProps('description')} />
                <Group grow>
                  <TextInput label="Agency" {...manualForm.getInputProps('agency')} />
                  <TextInput label="Solicitation #" {...manualForm.getInputProps('solicitation_number')} />
                </Group>
                <Group grow>
                  <TextInput label="NAICS Code" {...manualForm.getInputProps('naics_code')} />
                  <TextInput label="Set-Aside" {...manualForm.getInputProps('set_aside_type')} />
                </Group>
                <Group grow>
                  <TextInput label="Deadline" type="datetime-local" {...manualForm.getInputProps('response_deadline')} />
                </Group>
                <Group grow>
                  <TextInput label="Contact Name" {...manualForm.getInputProps('contact_name')} />
                  <TextInput label="Contact Email" {...manualForm.getInputProps('contact_email')} />
                </Group>
                <Button type="submit" loading={manualMutation.isPending}>Create</Button>
              </Stack>
            </form>
          </Tabs.Panel>

          <Tabs.Panel value="upload" pt="md">
            <Dropzone
              onDrop={(files) => uploadMutation.mutate(files)}
              loading={uploadMutation.isPending}
              accept={[MIME_TYPES.pdf, MIME_TYPES.docx, 'text/plain']}
              maxSize={50 * 1024 * 1024}
              maxFiles={1}
            >
              <Group justify="center" gap="xl" style={{ minHeight: 120, pointerEvents: 'none' }}>
                <Dropzone.Idle><IconFile size={40} /></Dropzone.Idle>
                <div>
                  <Text size="lg" inline>Drop a PDF or DOCX file</Text>
                  <Text size="sm" c="dimmed" inline mt={7}>AI will extract opportunity fields automatically</Text>
                </div>
              </Group>
            </Dropzone>
          </Tabs.Panel>

          <Tabs.Panel value="paste" pt="md">
            <Stack>
              <Textarea
                label="Paste opportunity text"
                placeholder="Paste the full text of the opportunity here..."
                minRows={8}
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
              />
              <Button
                onClick={() => pasteText && pasteMutation.mutate(pasteText)}
                loading={pasteMutation.isPending}
                disabled={!pasteText.trim()}
              >
                Create from Text
              </Button>
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </Modal>
    </Stack>
  )
}
