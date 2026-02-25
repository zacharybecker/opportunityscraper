import { useEffect, useState } from 'react'
import {
  Title, Stack, Tabs, Card, NumberInput, Switch, Button, Group,
  TextInput, MultiSelect, Text, Loader, Center, ActionIcon,
  Textarea, Badge, Table,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconPlus, IconTrash } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRelevancySettings, updateRelevancySettings,
  getGoals, updateGoals,
  getNotificationRules, createNotificationRule, updateNotificationRule, deleteNotificationRule,
} from '../api'
import { notifications } from '@mantine/notifications'

function RelevancyTab() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['relevancy-settings'], queryFn: getRelevancySettings })

  const form = useForm({
    initialValues: {
      min_relevancy_threshold: 30,
      naics_weight: 1.0,
      psc_weight: 1.0,
      set_aside_weight: 1.5,
      past_performance_weight: 1.2,
      future_goals_weight: 0.8,
      state_preferences: [] as string[],
      excluded_agencies: [] as string[],
      auto_pipeline: true,
    },
  })

  useEffect(() => { if (data) form.setValues(data as any) }, [data])

  const saveMutation = useMutation({
    mutationFn: (values: any) => updateRelevancySettings(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['relevancy-settings'] })
      notifications.show({ title: 'Saved', message: 'Relevancy settings updated', color: 'green' })
    },
  })

  if (isLoading) return <Loader />

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <form onSubmit={form.onSubmit((v) => saveMutation.mutate(v))}>
        <Stack>
          <NumberInput label="Minimum Relevancy Threshold" min={0} max={100} {...form.getInputProps('min_relevancy_threshold')} />
          <Group grow>
            <NumberInput label="NAICS Weight" step={0.1} decimalScale={1} {...form.getInputProps('naics_weight')} />
            <NumberInput label="PSC Weight" step={0.1} decimalScale={1} {...form.getInputProps('psc_weight')} />
          </Group>
          <Group grow>
            <NumberInput label="Set-Aside Weight" step={0.1} decimalScale={1} {...form.getInputProps('set_aside_weight')} />
            <NumberInput label="Past Performance Weight" step={0.1} decimalScale={1} {...form.getInputProps('past_performance_weight')} />
          </Group>
          <NumberInput label="Future Goals Weight" step={0.1} decimalScale={1} {...form.getInputProps('future_goals_weight')} />
          <MultiSelect
            label="State Preferences"
            data={form.values.state_preferences.map((s) => ({ value: s, label: s }))}
            {...form.getInputProps('state_preferences')}
            searchable creatable
            getCreateLabel={(q) => `+ ${q}`}
            onCreate={(q) => { form.setFieldValue('state_preferences', [...form.values.state_preferences, q]); return q }}
          />
          <Switch label="Auto-add to pipeline when above threshold" {...form.getInputProps('auto_pipeline', { type: 'checkbox' })} />
          <Button type="submit" loading={saveMutation.isPending}>Save Settings</Button>
        </Stack>
      </form>
    </Card>
  )
}

function GoalsTab() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['goals'], queryFn: getGoals })
  const [goals, setGoals] = useState<any[]>([])

  useEffect(() => { if (data) setGoals(data) }, [data])

  const saveMutation = useMutation({
    mutationFn: () => updateGoals(goals),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] })
      notifications.show({ title: 'Saved', message: 'Goals updated', color: 'green' })
    },
  })

  if (isLoading) return <Loader />

  return (
    <Stack>
      <Group justify="space-between">
        <Text fw={500}>Future Growth Goals</Text>
        <Button size="xs" leftSection={<IconPlus size={14} />}
          onClick={() => setGoals([...goals, { id: crypto.randomUUID(), title: '', description: '', target_naics: [], target_keywords: [], priority: 5, active: true }])}
        >
          Add Goal
        </Button>
      </Group>
      {goals.map((goal, i) => (
        <Card key={goal.id || i} shadow="xs" padding="sm" withBorder>
          <Group align="flex-start">
            <Stack style={{ flex: 1 }} gap="xs">
              <TextInput placeholder="Goal title" value={goal.title}
                onChange={(e) => { const g = [...goals]; g[i] = { ...g[i], title: e.target.value }; setGoals(g) }}
              />
              <Textarea placeholder="Description" value={goal.description} minRows={2}
                onChange={(e) => { const g = [...goals]; g[i] = { ...g[i], description: e.target.value }; setGoals(g) }}
              />
              <Group grow>
                <NumberInput label="Priority" min={1} max={10} value={goal.priority}
                  onChange={(v) => { const g = [...goals]; g[i] = { ...g[i], priority: v }; setGoals(g) }}
                />
                <Switch label="Active" checked={goal.active} mt="xl"
                  onChange={(e) => { const g = [...goals]; g[i] = { ...g[i], active: e.target.checked }; setGoals(g) }}
                />
              </Group>
            </Stack>
            <ActionIcon color="red" variant="subtle" onClick={() => setGoals(goals.filter((_, j) => j !== i))}>
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
        </Card>
      ))}
      <Button onClick={() => saveMutation.mutate()} loading={saveMutation.isPending}>Save Goals</Button>
    </Stack>
  )
}

function NotificationsTab() {
  const queryClient = useQueryClient()
  const { data: rules, isLoading } = useQuery({ queryKey: ['notification-rules'], queryFn: getNotificationRules })

  const createMutation = useMutation({
    mutationFn: createNotificationRule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notification-rules'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteNotificationRule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notification-rules'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_enabled }: { id: string; is_enabled: boolean }) =>
      updateNotificationRule(id, { is_enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notification-rules'] }),
  })

  if (isLoading) return <Loader />

  return (
    <Stack>
      <Group justify="space-between">
        <Text fw={500}>Notification Rules</Text>
        <Button size="xs" leftSection={<IconPlus size={14} />}
          onClick={() => createMutation.mutate({
            name: 'New Rule',
            trigger_type: 'high_relevancy',
            channels: ['email'],
          })}
        >
          Add Rule
        </Button>
      </Group>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Trigger</Table.Th>
            <Table.Th>Channels</Table.Th>
            <Table.Th>Enabled</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rules?.map((rule) => (
            <Table.Tr key={rule.id}>
              <Table.Td>{rule.name}</Table.Td>
              <Table.Td><Badge variant="light">{rule.trigger_type}</Badge></Table.Td>
              <Table.Td>{rule.channels?.join(', ') || '-'}</Table.Td>
              <Table.Td>
                <Switch checked={rule.is_enabled}
                  onChange={() => toggleMutation.mutate({ id: rule.id, is_enabled: !rule.is_enabled })}
                />
              </Table.Td>
              <Table.Td>
                <Button size="xs" variant="subtle" color="red" onClick={() => deleteMutation.mutate(rule.id)}>Delete</Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  )
}

export default function Settings() {
  return (
    <Stack>
      <Title order={2}>Settings</Title>
      <Tabs defaultValue="relevancy">
        <Tabs.List>
          <Tabs.Tab value="relevancy">Relevancy Settings</Tabs.Tab>
          <Tabs.Tab value="goals">Future Goals</Tabs.Tab>
          <Tabs.Tab value="notifications">Notifications</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="relevancy" pt="md"><RelevancyTab /></Tabs.Panel>
        <Tabs.Panel value="goals" pt="md"><GoalsTab /></Tabs.Panel>
        <Tabs.Panel value="notifications" pt="md"><NotificationsTab /></Tabs.Panel>
      </Tabs>
    </Stack>
  )
}
