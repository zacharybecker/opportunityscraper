import { useState } from 'react'
import {
  Title, Stack, Card, Table, Button, Group, Badge, Modal,
  TextInput, Select, Switch, Textarea, Loader, Center, Text,
  JsonInput,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconPlus, IconPlayerPlay, IconPlayerPlayFilled } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import {
  getScrapers, createScraper, updateScraper, deleteScraper,
  runScraper, runAllScrapers, getScraperRuns,
} from '../api'
import { notifications } from '@mantine/notifications'
import type { ScraperConfig, ScrapeRun } from '../types'

dayjs.extend(relativeTime)

export default function Scrapers() {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ScraperConfig | null>(null)
  const [runsFor, setRunsFor] = useState<string | null>(null)

  const { data: scrapers, isLoading } = useQuery({
    queryKey: ['scrapers'],
    queryFn: getScrapers,
  })

  const { data: runs } = useQuery({
    queryKey: ['scraper-runs', runsFor],
    queryFn: () => getScraperRuns(runsFor!),
    enabled: !!runsFor,
  })

  const form = useForm({
    initialValues: {
      name: '',
      scraper_type: 'sam_gov',
      is_enabled: true,
      config: '{}',
      schedule_cron: '',
    },
  })

  const saveMutation = useMutation({
    mutationFn: (values: any) => {
      const data = { ...values, config: JSON.parse(values.config) }
      return editing ? updateScraper(editing.id, data) : createScraper(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scrapers'] })
      setModalOpen(false)
      setEditing(null)
      form.reset()
      notifications.show({ title: 'Saved', message: 'Scraper configuration saved', color: 'green' })
    },
    onError: () => notifications.show({ title: 'Error', message: 'Failed to save', color: 'red' }),
  })

  const runMutation = useMutation({
    mutationFn: runScraper,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scrapers'] })
      notifications.show({ title: 'Running', message: 'Scrape job started', color: 'blue' })
    },
  })

  const runAllMutation = useMutation({
    mutationFn: runAllScrapers,
    onSuccess: (data) => {
      notifications.show({ title: 'Running', message: `${data.count} scrapers queued`, color: 'blue' })
    },
  })

  const delMutation = useMutation({
    mutationFn: deleteScraper,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scrapers'] }),
  })

  const openEdit = (s: ScraperConfig) => {
    setEditing(s)
    form.setValues({
      name: s.name,
      scraper_type: s.scraper_type,
      is_enabled: s.is_enabled,
      config: JSON.stringify(s.config, null, 2),
      schedule_cron: s.schedule_cron || '',
    })
    setModalOpen(true)
  }

  if (isLoading) return <Center h={400}><Loader /></Center>

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Scrapers</Title>
        <Group>
          <Button
            leftSection={<IconPlayerPlayFilled size={16} />}
            variant="light"
            onClick={() => runAllMutation.mutate()}
            loading={runAllMutation.isPending}
          >
            Run All
          </Button>
          <Button leftSection={<IconPlus size={16} />} onClick={() => { setEditing(null); form.reset(); setModalOpen(true) }}>
            Add Scraper
          </Button>
        </Group>
      </Group>

      <Card shadow="sm" padding={0} radius="md" withBorder>
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Enabled</Table.Th>
              <Table.Th>Schedule</Table.Th>
              <Table.Th>Last Run</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {scrapers?.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td>{s.name}</Table.Td>
                <Table.Td><Badge variant="light">{s.scraper_type === 'sam_gov' ? 'SAM.gov' : 'Web'}</Badge></Table.Td>
                <Table.Td><Badge color={s.is_enabled ? 'green' : 'gray'}>{s.is_enabled ? 'Yes' : 'No'}</Badge></Table.Td>
                <Table.Td><Text size="sm">{s.schedule_cron || 'Manual'}</Text></Table.Td>
                <Table.Td><Text size="sm">{s.last_run_at ? dayjs(s.last_run_at).fromNow() : 'Never'}</Text></Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" variant="light" leftSection={<IconPlayerPlay size={14} />}
                      onClick={() => runMutation.mutate(s.id)} loading={runMutation.isPending}>
                      Run
                    </Button>
                    <Button size="xs" variant="subtle" onClick={() => openEdit(s)}>Edit</Button>
                    <Button size="xs" variant="subtle" onClick={() => setRunsFor(runsFor === s.id ? null : s.id)}>History</Button>
                    <Button size="xs" variant="subtle" color="red" onClick={() => delMutation.mutate(s.id)}>Delete</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {!scrapers?.length && (
              <Table.Tr><Table.Td colSpan={6}><Text ta="center" c="dimmed" py="lg">No scrapers configured</Text></Table.Td></Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {runsFor && runs && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="md">Run History</Title>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Status</Table.Th>
                <Table.Th>Trigger</Table.Th>
                <Table.Th>Results</Table.Th>
                <Table.Th>Started</Table.Th>
                <Table.Th>Duration</Table.Th>
                <Table.Th>Error</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {runs.map((r: ScrapeRun) => (
                <Table.Tr key={r.id}>
                  <Table.Td><Badge color={r.status === 'completed' ? 'green' : r.status === 'failed' ? 'red' : 'yellow'}>{r.status}</Badge></Table.Td>
                  <Table.Td>{r.trigger_type}</Table.Td>
                  <Table.Td>{r.stats?.found ? `${r.stats.new} new / ${r.stats.found} found` : '-'}</Table.Td>
                  <Table.Td>{r.started_at ? dayjs(r.started_at).format('MMM D HH:mm') : '-'}</Table.Td>
                  <Table.Td>
                    {r.started_at && r.completed_at ? `${dayjs(r.completed_at).diff(dayjs(r.started_at), 'second')}s` : '-'}
                  </Table.Td>
                  <Table.Td><Text size="xs" c="red" lineClamp={1}>{r.error_message || '-'}</Text></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Scraper' : 'New Scraper'} size="lg">
        <form onSubmit={form.onSubmit((v) => saveMutation.mutate(v))}>
          <Stack>
            <TextInput label="Name" required {...form.getInputProps('name')} />
            <Select
              label="Type"
              data={[
                { value: 'sam_gov', label: 'SAM.gov API' },
                { value: 'generic_web', label: 'Generic Web Scraper' },
              ]}
              {...form.getInputProps('scraper_type')}
              disabled={!!editing}
            />
            <Switch label="Enabled" {...form.getInputProps('is_enabled', { type: 'checkbox' })} />
            <TextInput label="Schedule (cron)" placeholder="0 6 * * *" {...form.getInputProps('schedule_cron')} />
            <JsonInput
              label="Configuration (JSON)"
              minRows={8}
              formatOnBlur
              {...form.getInputProps('config')}
            />
            <Button type="submit" loading={saveMutation.isPending}>Save</Button>
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}
