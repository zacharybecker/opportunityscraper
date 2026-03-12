import { useState } from 'react'
import {
  Title, Stack, Card, Group, Button, Text, Badge, Table,
  Modal, TextInput, Select, Loader, Center,
} from '@mantine/core'
import { IconPlus } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { notifications } from '@mantine/notifications'
import apiClient from '../api/client'

const statusColors: Record<string, string> = {
  draft: 'gray',
  review: 'yellow',
  submitted: 'blue',
  final: 'green',
}

export default function Proposals() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [oppId, setOppId] = useState('')

  const { data: proposals, isLoading } = useQuery({
    queryKey: ['proposals'],
    queryFn: () => apiClient.get('/proposals').then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      apiClient.post('/proposals', {
        title,
        opportunity_id: oppId || undefined,
      }).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['proposals'] })
      setCreateOpen(false)
      setTitle('')
      setOppId('')
      navigate(`/proposals/${data.id}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/proposals/${id}`).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['proposals'] }),
  })

  if (isLoading) return <Center h={400}><Loader /></Center>

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Proposals</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setCreateOpen(true)}>
          New Proposal
        </Button>
      </Group>

      <Card shadow="sm" padding={0} radius="md" withBorder>
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Title</Table.Th>
              <Table.Th>Opportunity</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Updated</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {proposals?.map((p: any) => (
              <Table.Tr key={p.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/proposals/${p.id}`)}>
                <Table.Td><Text size="sm" fw={500}>{p.title}</Text></Table.Td>
                <Table.Td><Text size="sm" lineClamp={1}>{p.opportunity_title || '-'}</Text></Table.Td>
                <Table.Td><Badge color={statusColors[p.status] || 'gray'}>{p.status}</Badge></Table.Td>
                <Table.Td><Text size="sm">{dayjs(p.updated_at).format('MMM D, HH:mm')}</Text></Table.Td>
                <Table.Td>
                  <Button
                    size="xs" variant="subtle" color="red"
                    onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(p.id) }}
                  >
                    Delete
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
            {!proposals?.length && (
              <Table.Tr>
                <Table.Td colSpan={5}><Text ta="center" c="dimmed" py="xl">No proposals yet</Text></Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="New Proposal">
        <Stack>
          <TextInput label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <TextInput label="Opportunity ID (optional)" value={oppId} onChange={(e) => setOppId(e.target.value)} placeholder="Paste opportunity ID" />
          <Button onClick={() => createMutation.mutate()} loading={createMutation.isPending} disabled={!title}>
            Create
          </Button>
        </Stack>
      </Modal>
    </Stack>
  )
}
