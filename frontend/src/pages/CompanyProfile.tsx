import { useEffect } from 'react'
import {
  Title, Stack, Card, TextInput, Textarea, NumberInput, Button,
  Group, MultiSelect, TagsInput, Loader, Center, Text, ActionIcon,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconPlus, IconTrash } from '@tabler/icons-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCompany, updateCompany } from '../api'
import { notifications } from '@mantine/notifications'

const SMALL_BIZ_OPTIONS = [
  { value: '8a', label: '8(a)' },
  { value: 'HUBZone', label: 'HUBZone' },
  { value: 'SDVOSB', label: 'SDVOSB' },
  { value: 'WOSB', label: 'WOSB' },
  { value: 'EDWOSB', label: 'EDWOSB' },
]

export default function CompanyProfile() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['company'],
    queryFn: getCompany,
  })

  const form = useForm({
    initialValues: {
      name: '',
      uei_sam: '',
      cage_code: '',
      description: '',
      capabilities: [] as { name: string; description: string }[],
      small_business_types: [] as string[],
      naics_codes: [] as string[],
      certifications: [] as { type: string; number: string; issued: string; expiry: string; details: string }[],
      past_performance: [] as { name: string; agency: string; contract_num: string; value: number; start: string; end: string; description: string }[],
      employee_count: null as number | null,
      annual_revenue: null as number | null,
    },
  })

  useEffect(() => {
    if (data) {
      form.setValues({
        name: data.name || '',
        uei_sam: data.uei_sam || '',
        cage_code: data.cage_code || '',
        description: data.description || '',
        capabilities: data.capabilities || [],
        small_business_types: data.small_business_types || [],
        naics_codes: data.naics_codes || [],
        certifications: data.certifications || [],
        past_performance: data.past_performance || [],
        employee_count: data.employee_count,
        annual_revenue: data.annual_revenue,
      })
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: (values: any) => updateCompany(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company'] })
      notifications.show({ title: 'Saved', message: 'Company profile updated', color: 'green' })
    },
    onError: () => {
      notifications.show({ title: 'Error', message: 'Failed to save', color: 'red' })
    },
  })

  if (isLoading) return <Center h={400}><Loader /></Center>

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Company Profile</Title>
        <Button onClick={() => saveMutation.mutate(form.values)} loading={saveMutation.isPending}>
          Save Changes
        </Button>
      </Group>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Title order={4} mb="md">Basic Information</Title>
        <Stack>
          <TextInput label="Company Name" {...form.getInputProps('name')} />
          <Group grow>
            <TextInput label="UEI (SAM)" {...form.getInputProps('uei_sam')} />
            <TextInput label="CAGE Code" {...form.getInputProps('cage_code')} />
          </Group>
          <Textarea label="Description / Capabilities Narrative" minRows={4} {...form.getInputProps('description')} />
          <Group grow>
            <NumberInput label="Employee Count" {...form.getInputProps('employee_count')} />
            <NumberInput label="Annual Revenue ($)" prefix="$" thousandSeparator="," {...form.getInputProps('annual_revenue')} />
          </Group>
          <MultiSelect
            label="Small Business Types"
            data={SMALL_BIZ_OPTIONS}
            {...form.getInputProps('small_business_types')}
          />
          <TagsInput
            label="NAICS Codes"
            {...form.getInputProps('naics_codes')}
          />
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group justify="space-between" mb="md">
          <Title order={4}>Capabilities</Title>
          <Button
            size="xs"
            leftSection={<IconPlus size={14} />}
            variant="light"
            onClick={() => form.setFieldValue('capabilities', [...form.values.capabilities, { name: '', description: '' }])}
          >
            Add
          </Button>
        </Group>
        <Stack>
          {form.values.capabilities.map((cap, i) => (
            <Group key={i} align="flex-start">
              <TextInput
                placeholder="Capability name"
                value={cap.name}
                onChange={(e) => {
                  const caps = [...form.values.capabilities]
                  caps[i] = { ...caps[i], name: e.target.value }
                  form.setFieldValue('capabilities', caps)
                }}
                style={{ flex: 1 }}
              />
              <TextInput
                placeholder="Description"
                value={cap.description}
                onChange={(e) => {
                  const caps = [...form.values.capabilities]
                  caps[i] = { ...caps[i], description: e.target.value }
                  form.setFieldValue('capabilities', caps)
                }}
                style={{ flex: 2 }}
              />
              <ActionIcon
                color="red" variant="subtle"
                onClick={() => form.setFieldValue('capabilities', form.values.capabilities.filter((_, j) => j !== i))}
              >
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}
          {form.values.capabilities.length === 0 && <Text c="dimmed" size="sm">No capabilities added</Text>}
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group justify="space-between" mb="md">
          <Title order={4}>Certifications</Title>
          <Button
            size="xs" leftSection={<IconPlus size={14} />} variant="light"
            onClick={() => form.setFieldValue('certifications', [...form.values.certifications, { type: '', number: '', issued: '', expiry: '', details: '' }])}
          >
            Add
          </Button>
        </Group>
        <Stack>
          {form.values.certifications.map((cert, i) => (
            <Group key={i} align="flex-start">
              <TextInput placeholder="Type" value={cert.type} style={{ flex: 1 }}
                onChange={(e) => { const c = [...form.values.certifications]; c[i] = { ...c[i], type: e.target.value }; form.setFieldValue('certifications', c) }}
              />
              <TextInput placeholder="Number" value={cert.number} style={{ flex: 1 }}
                onChange={(e) => { const c = [...form.values.certifications]; c[i] = { ...c[i], number: e.target.value }; form.setFieldValue('certifications', c) }}
              />
              <TextInput placeholder="Expiry" value={cert.expiry} style={{ flex: 1 }}
                onChange={(e) => { const c = [...form.values.certifications]; c[i] = { ...c[i], expiry: e.target.value }; form.setFieldValue('certifications', c) }}
              />
              <ActionIcon color="red" variant="subtle"
                onClick={() => form.setFieldValue('certifications', form.values.certifications.filter((_, j) => j !== i))}
              >
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}
          {form.values.certifications.length === 0 && <Text c="dimmed" size="sm">No certifications added</Text>}
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group justify="space-between" mb="md">
          <Title order={4}>Past Performance</Title>
          <Button
            size="xs" leftSection={<IconPlus size={14} />} variant="light"
            onClick={() => form.setFieldValue('past_performance', [...form.values.past_performance, { name: '', agency: '', contract_num: '', value: 0, start: '', end: '', description: '' }])}
          >
            Add
          </Button>
        </Group>
        <Stack>
          {form.values.past_performance.map((perf, i) => (
            <Card key={i} withBorder padding="sm">
              <Group align="flex-start">
                <Stack style={{ flex: 1 }} gap="xs">
                  <TextInput placeholder="Contract Name" value={perf.name} size="sm"
                    onChange={(e) => { const p = [...form.values.past_performance]; p[i] = { ...p[i], name: e.target.value }; form.setFieldValue('past_performance', p) }}
                  />
                  <Group grow>
                    <TextInput placeholder="Agency" value={perf.agency} size="sm"
                      onChange={(e) => { const p = [...form.values.past_performance]; p[i] = { ...p[i], agency: e.target.value }; form.setFieldValue('past_performance', p) }}
                    />
                    <TextInput placeholder="Contract #" value={perf.contract_num} size="sm"
                      onChange={(e) => { const p = [...form.values.past_performance]; p[i] = { ...p[i], contract_num: e.target.value }; form.setFieldValue('past_performance', p) }}
                    />
                  </Group>
                  <Textarea placeholder="Description" value={perf.description} size="sm" minRows={2}
                    onChange={(e) => { const p = [...form.values.past_performance]; p[i] = { ...p[i], description: e.target.value }; form.setFieldValue('past_performance', p) }}
                  />
                </Stack>
                <ActionIcon color="red" variant="subtle"
                  onClick={() => form.setFieldValue('past_performance', form.values.past_performance.filter((_, j) => j !== i))}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Group>
            </Card>
          ))}
          {form.values.past_performance.length === 0 && <Text c="dimmed" size="sm">No past performance added</Text>}
        </Stack>
      </Card>
    </Stack>
  )
}
