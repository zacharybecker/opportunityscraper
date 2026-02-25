import { useState } from 'react'
import {
  Title, Stack, Tabs, Card, Table, Button, Group, Badge,
  Modal, TextInput, Select, Switch, Text, Loader, Center,
  Code,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconPlus } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import {
  getLdapGroups, createLdapGroup, updateLdapGroup, deleteLdapGroup,
  getUsers, updateUser,
  getAiConfig, updateAiConfig,
  getHealth,
} from '../api'
import { notifications } from '@mantine/notifications'
import type { LdapGroupRole, User } from '../types'

function LdapGroupsTab() {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const { data: groups, isLoading } = useQuery({ queryKey: ['ldap-groups'], queryFn: getLdapGroups })

  const form = useForm({ initialValues: { group_dn: '', group_name: '', role: 'viewer' } })

  const createMutation = useMutation({
    mutationFn: createLdapGroup,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ldap-groups'] }); setModalOpen(false); form.reset() },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteLdapGroup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ldap-groups'] }),
  })

  if (isLoading) return <Loader />

  return (
    <Stack>
      <Group justify="flex-end">
        <Button leftSection={<IconPlus size={14} />} onClick={() => setModalOpen(true)}>Add Mapping</Button>
      </Group>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Group DN</Table.Th>
            <Table.Th>Name</Table.Th>
            <Table.Th>Role</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {groups?.map((g: LdapGroupRole) => (
            <Table.Tr key={g.id}>
              <Table.Td><Code>{g.group_dn}</Code></Table.Td>
              <Table.Td>{g.group_name}</Table.Td>
              <Table.Td><Badge>{g.role}</Badge></Table.Td>
              <Table.Td>
                <Button size="xs" variant="subtle" color="red" onClick={() => deleteMutation.mutate(g.id)}>Delete</Button>
              </Table.Td>
            </Table.Tr>
          ))}
          {!groups?.length && <Table.Tr><Table.Td colSpan={4}><Text c="dimmed" ta="center">No mappings</Text></Table.Td></Table.Tr>}
        </Table.Tbody>
      </Table>
      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Add LDAP Group Mapping">
        <form onSubmit={form.onSubmit((v) => createMutation.mutate(v))}>
          <Stack>
            <TextInput label="Group DN" required {...form.getInputProps('group_dn')} />
            <TextInput label="Group Name" required {...form.getInputProps('group_name')} />
            <Select label="Role" data={['admin', 'analyst', 'viewer']} {...form.getInputProps('role')} />
            <Button type="submit" loading={createMutation.isPending}>Create</Button>
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}

function UsersTab() {
  const queryClient = useQueryClient()
  const { data: users, isLoading } = useQuery({ queryKey: ['users'], queryFn: getUsers })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => updateUser(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  if (isLoading) return <Loader />

  return (
    <Table>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Username</Table.Th>
          <Table.Th>Display Name</Table.Th>
          <Table.Th>Role</Table.Th>
          <Table.Th>Active</Table.Th>
          <Table.Th>Last Login</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {users?.map((u: User) => (
          <Table.Tr key={u.id}>
            <Table.Td>{u.username}</Table.Td>
            <Table.Td>{u.display_name || '-'}</Table.Td>
            <Table.Td><Badge>{u.role}{u.is_superadmin ? ' (SA)' : ''}</Badge></Table.Td>
            <Table.Td>
              <Switch checked={u.is_active}
                onChange={() => toggleMutation.mutate({ id: u.id, is_active: !u.is_active })}
              />
            </Table.Td>
            <Table.Td>{u.last_login ? dayjs(u.last_login).format('MMM D, YYYY HH:mm') : 'Never'}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  )
}

function AIConfigTab() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['ai-config'], queryFn: getAiConfig })

  const form = useForm({ initialValues: { api_base_url: '', model: '', max_tokens: 4096, temperature: 0.3, api_key: '' } })

  const saveMutation = useMutation({
    mutationFn: (values: any) => updateAiConfig(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-config'] })
      notifications.show({ title: 'Saved', message: 'AI configuration updated', color: 'green' })
    },
  })

  if (isLoading) return <Loader />

  if (data && !form.isDirty()) {
    form.setValues({
      api_base_url: data.api_base_url || '',
      model: data.model || '',
      max_tokens: data.max_tokens || 4096,
      temperature: data.temperature || 0.3,
      api_key: '',
    })
  }

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <form onSubmit={form.onSubmit((v) => saveMutation.mutate(v))}>
        <Stack>
          <TextInput label="API Base URL" {...form.getInputProps('api_base_url')} />
          <TextInput label="API Key" type="password" placeholder="Leave blank to keep current" {...form.getInputProps('api_key')} />
          <TextInput label="Model" {...form.getInputProps('model')} />
          <Group grow>
            <TextInput label="Max Tokens" type="number" {...form.getInputProps('max_tokens')} />
            <TextInput label="Temperature" type="number" step="0.1" {...form.getInputProps('temperature')} />
          </Group>
          <Button type="submit" loading={saveMutation.isPending}>Save</Button>
        </Stack>
      </form>
    </Card>
  )
}

function HealthTab() {
  const { data, isLoading, refetch } = useQuery({ queryKey: ['health'], queryFn: getHealth })

  if (isLoading) return <Loader />

  return (
    <Stack>
      <Group justify="flex-end">
        <Button variant="light" onClick={() => refetch()}>Refresh</Button>
      </Group>
      <Card shadow="sm" padding="lg" radius="md" withBorder>
        {data && Object.entries(data).map(([key, value]) => (
          <Group key={key} justify="space-between" py="xs" style={{ borderBottom: '1px solid var(--mantine-color-gray-2)' }}>
            <Text fw={500}>{key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}</Text>
            <Badge color={value === 'ok' || value === true ? 'green' : typeof value === 'string' && value.startsWith('error') ? 'red' : 'blue'}>
              {String(value)}
            </Badge>
          </Group>
        ))}
      </Card>
    </Stack>
  )
}

export default function Admin() {
  return (
    <Stack>
      <Title order={2}>Admin</Title>
      <Tabs defaultValue="ldap">
        <Tabs.List>
          <Tabs.Tab value="ldap">LDAP Groups</Tabs.Tab>
          <Tabs.Tab value="users">Users</Tabs.Tab>
          <Tabs.Tab value="ai">AI Config</Tabs.Tab>
          <Tabs.Tab value="health">System Health</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="ldap" pt="md"><LdapGroupsTab /></Tabs.Panel>
        <Tabs.Panel value="users" pt="md"><UsersTab /></Tabs.Panel>
        <Tabs.Panel value="ai" pt="md"><AIConfigTab /></Tabs.Panel>
        <Tabs.Panel value="health" pt="md"><HealthTab /></Tabs.Panel>
      </Tabs>
    </Stack>
  )
}
