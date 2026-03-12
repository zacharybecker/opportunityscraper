import { useState } from 'react'
import {
  Title, Stack, Card, Table, Button, Group, Badge, Modal,
  TextInput, Select, Switch, Textarea, Loader, Center, Text,
  JsonInput, Tabs, NumberInput, MultiSelect, Alert,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconPlus, IconPlayerPlay, IconPlayerPlayFilled, IconTestPipe, IconInfoCircle } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import {
  getScrapers, createScraper, updateScraper, deleteScraper,
  runScraper, runAllScrapers, getScraperRuns, testScraper,
} from '../api'
import { notifications } from '@mantine/notifications'
import type { ScraperConfig, ScrapeRun } from '../types'

dayjs.extend(relativeTime)

function SamGovConfigForm({ form }: { form: any }) {
  return (
    <Stack>
      <TextInput label="API Key" required placeholder="Your SAM.gov API key" {...form.getInputProps('sam_api_key')} />
      <TextInput label="Keywords" placeholder="Comma-separated keywords"
        value={form.values.sam_keywords}
        onChange={(e) => form.setFieldValue('sam_keywords', e.target.value)}
      />
      <TextInput label="NAICS Codes" placeholder="Comma-separated (e.g., 541512,541519)"
        value={form.values.sam_naics}
        onChange={(e) => form.setFieldValue('sam_naics', e.target.value)}
      />
      <Select label="Set-Aside Type" clearable
        data={[
          { value: 'SBA', label: 'Small Business' },
          { value: 'SBP', label: 'Small Business Set-Aside' },
          { value: '8A', label: '8(a)' },
          { value: 'HZC', label: 'HUBZone' },
          { value: 'SDVOSBC', label: 'SDVOSB' },
          { value: 'WOSB', label: 'WOSB' },
        ]}
        {...form.getInputProps('sam_set_aside')}
      />
      <TextInput label="States" placeholder="Comma-separated state codes (e.g., VA,MD,DC)"
        value={form.values.sam_states}
        onChange={(e) => form.setFieldValue('sam_states', e.target.value)}
      />
      <NumberInput label="Lookback Days" min={1} max={365} {...form.getInputProps('sam_lookback')} />
    </Stack>
  )
}

function WebScraperConfigForm({ form }: { form: any }) {
  return (
    <Stack>
      <TextInput label="Search URL" required placeholder="https://example.com/opportunities" {...form.getInputProps('web_search_url')} />
      <TextInput label="Base URL" placeholder="https://example.com (for resolving relative links)" {...form.getInputProps('web_base_url')} />
      <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
        CSS selectors tell the scraper how to find opportunities on the page.
      </Alert>
      <TextInput label="Listing Row Selector" placeholder="tr, .opportunity-row, .listing-item" {...form.getInputProps('web_listing_selector')} />
      <TextInput label="Title Selector" placeholder="a, .title, h3" {...form.getInputProps('web_title_selector')} />
      <TextInput label="Detail Link Selector" placeholder="a@href (use @ to specify attribute)" {...form.getInputProps('web_link_selector')} />
      <TextInput label="Deadline Selector" placeholder=".deadline, td:nth-child(3)" {...form.getInputProps('web_deadline_selector')} />
      <TextInput label="Description Selector (on detail page)" placeholder=".description, #content" {...form.getInputProps('web_description_selector')} />
      <TextInput label="Date Format" placeholder="%m/%d/%Y" {...form.getInputProps('web_date_format')} />
      <NumberInput label="Request Delay (ms)" min={0} max={10000} {...form.getInputProps('web_delay')} />
      <NumberInput label="Max Pages" min={1} max={50} {...form.getInputProps('web_max_pages')} />
    </Stack>
  )
}

function buildConfig(values: any): Record<string, any> {
  if (values.scraper_type === 'sam_gov') {
    const config: any = { api_key: values.sam_api_key }
    if (values.sam_keywords) config.keywords = values.sam_keywords.split(',').map((s: string) => s.trim()).filter(Boolean)
    if (values.sam_naics) config.naics_codes = values.sam_naics.split(',').map((s: string) => s.trim()).filter(Boolean)
    if (values.sam_set_aside) config.set_aside_types = [values.sam_set_aside]
    if (values.sam_states) config.states = values.sam_states.split(',').map((s: string) => s.trim()).filter(Boolean)
    if (values.sam_lookback) config.lookback_days = values.sam_lookback
    return config
  }

  // generic_web
  const selectors: any = {}
  if (values.web_listing_selector) selectors.listing_row = values.web_listing_selector
  if (values.web_title_selector) selectors.title = values.web_title_selector
  if (values.web_link_selector) selectors.detail_link = values.web_link_selector
  if (values.web_deadline_selector) selectors.deadline = values.web_deadline_selector
  if (values.web_description_selector) selectors.description = values.web_description_selector

  const config: any = {
    search_url: values.web_search_url,
    selectors,
  }
  if (values.web_base_url) config.base_url = values.web_base_url
  if (values.web_date_format) config.date_format = values.web_date_format
  if (values.web_delay) config.request_delay_ms = values.web_delay
  if (values.web_max_pages) config.pagination = { type: 'page_param', max_pages: values.web_max_pages }
  return config
}

function parseConfigToForm(scraper: ScraperConfig) {
  const c = scraper.config || {}
  if (scraper.scraper_type === 'sam_gov') {
    return {
      sam_api_key: c.api_key || '',
      sam_keywords: (c.keywords || []).join(', '),
      sam_naics: (c.naics_codes || []).join(', '),
      sam_set_aside: c.set_aside_types?.[0] || '',
      sam_states: (c.states || []).join(', '),
      sam_lookback: c.lookback_days || 30,
    }
  }
  const sel = c.selectors || {}
  return {
    web_search_url: c.search_url || '',
    web_base_url: c.base_url || '',
    web_listing_selector: sel.listing_row || '',
    web_title_selector: sel.title || '',
    web_link_selector: sel.detail_link || '',
    web_deadline_selector: sel.deadline || '',
    web_description_selector: sel.description || '',
    web_date_format: c.date_format || '',
    web_delay: c.request_delay_ms || 1000,
    web_max_pages: c.pagination?.max_pages || 10,
  }
}

export default function Scrapers() {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ScraperConfig | null>(null)
  const [runsFor, setRunsFor] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<any>(null)

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
      schedule_cron: '',
      // SAM.gov fields
      sam_api_key: '',
      sam_keywords: '',
      sam_naics: '',
      sam_set_aside: '',
      sam_states: '',
      sam_lookback: 30,
      // Web scraper fields
      web_search_url: '',
      web_base_url: '',
      web_listing_selector: '',
      web_title_selector: '',
      web_link_selector: '',
      web_deadline_selector: '',
      web_description_selector: '',
      web_date_format: '',
      web_delay: 1000,
      web_max_pages: 10,
    },
  })

  const saveMutation = useMutation({
    mutationFn: (values: any) => {
      const data = {
        name: values.name,
        scraper_type: values.scraper_type,
        is_enabled: values.is_enabled,
        schedule_cron: values.schedule_cron || null,
        config: buildConfig(values),
      }
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

  const testMutation = useMutation({
    mutationFn: testScraper,
    onSuccess: (data) => {
      setTestResults(data)
      if (data.status === 'ok') {
        notifications.show({ title: 'Test Complete', message: `Found ${data.count} results`, color: 'green' })
      } else {
        notifications.show({ title: 'Test Failed', message: data.message, color: 'red' })
      }
    },
    onError: () => notifications.show({ title: 'Error', message: 'Test failed', color: 'red' }),
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
    const configFields = parseConfigToForm(s)
    form.setValues({
      name: s.name,
      scraper_type: s.scraper_type,
      is_enabled: s.is_enabled,
      schedule_cron: s.schedule_cron || '',
      ...configFields,
    } as any)
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
          <Button leftSection={<IconPlus size={16} />} onClick={() => { setEditing(null); form.reset(); setTestResults(null); setModalOpen(true) }}>
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
                    <Button size="xs" variant="light" color="teal" leftSection={<IconTestPipe size={14} />}
                      onClick={() => testMutation.mutate(s.id)} loading={testMutation.isPending}>
                      Test
                    </Button>
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

      {testResults && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Group justify="space-between" mb="md">
            <Title order={4}>Test Results ({testResults.count || 0} found)</Title>
            <Button size="xs" variant="subtle" onClick={() => setTestResults(null)}>Close</Button>
          </Group>
          {testResults.status === 'error' ? (
            <Alert color="red">{testResults.message}</Alert>
          ) : (
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Title</Table.Th>
                  <Table.Th>Agency</Table.Th>
                  <Table.Th>Deadline</Table.Th>
                  <Table.Th>NAICS</Table.Th>
                  <Table.Th>Set-Aside</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {testResults.preview?.map((r: any, i: number) => (
                  <Table.Tr key={i}>
                    <Table.Td>
                      {r.source_url ? (
                        <Text size="sm" component="a" href={r.source_url} target="_blank" c="blue">{r.title}</Text>
                      ) : (
                        <Text size="sm">{r.title}</Text>
                      )}
                    </Table.Td>
                    <Table.Td><Text size="sm">{r.agency || '-'}</Text></Table.Td>
                    <Table.Td><Text size="sm">{r.response_deadline ? dayjs(r.response_deadline).format('MMM D, YYYY') : '-'}</Text></Table.Td>
                    <Table.Td><Text size="sm">{r.naics_code || '-'}</Text></Table.Td>
                    <Table.Td><Text size="sm">{r.set_aside_type || '-'}</Text></Table.Td>
                  </Table.Tr>
                ))}
                {!testResults.preview?.length && (
                  <Table.Tr><Table.Td colSpan={5}><Text ta="center" c="dimmed">No results</Text></Table.Td></Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      )}

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
            <TextInput label="Schedule (cron)" placeholder="0 6 * * * (daily at 6am)" {...form.getInputProps('schedule_cron')} />

            {form.values.scraper_type === 'sam_gov' ? (
              <SamGovConfigForm form={form} />
            ) : (
              <WebScraperConfigForm form={form} />
            )}

            <Button type="submit" loading={saveMutation.isPending}>Save</Button>
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}
