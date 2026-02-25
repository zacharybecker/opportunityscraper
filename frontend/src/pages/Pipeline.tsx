import {
  Title, Stack, Card, Text, Badge, Group, Button, Select,
  Loader, Center,
} from '@mantine/core'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { getPipeline, updatePipelineEntry, deletePipelineEntry } from '../api'
import { notifications } from '@mantine/notifications'
import type { PipelineEntry } from '../types'

const STAGES = [
  { key: 'found', label: 'Found', color: 'gray' },
  { key: 'reviewing', label: 'Reviewing', color: 'blue' },
  { key: 'pursuing', label: 'Pursuing', color: 'cyan' },
  { key: 'applied', label: 'Applied', color: 'violet' },
  { key: 'won', label: 'Won', color: 'green' },
  { key: 'lost', label: 'Lost', color: 'red' },
]

export default function Pipeline() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['pipeline'],
    queryFn: getPipeline,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...rest }: any) => updatePipelineEntry(id, rest),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
      notifications.show({ title: 'Updated', message: 'Pipeline entry updated', color: 'green' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deletePipelineEntry,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })

  if (isLoading) return <Center h={400}><Loader /></Center>

  return (
    <Stack>
      <Title order={2}>Pipeline</Title>

      <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 16 }}>
        {STAGES.map(({ key, label, color }) => {
          const entries: PipelineEntry[] = (data as any)?.[key] || []
          return (
            <div key={key} style={{ minWidth: 260, flex: 1 }}>
              <Group mb="xs" gap="xs">
                <Badge color={color} size="lg">{label}</Badge>
                <Badge variant="light" color="gray" size="sm">{entries.length}</Badge>
              </Group>
              <Stack gap="xs">
                {entries.map((entry) => {
                  const opp = (entry as any).opportunity
                  return (
                    <Card key={entry.id} shadow="xs" padding="sm" radius="sm" withBorder>
                      <Text
                        size="sm" fw={500} lineClamp={2}
                        style={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/opportunities/${entry.opportunity_id}`)}
                      >
                        {opp?.title || 'Opportunity'}
                      </Text>
                      <Group mt="xs" gap="xs">
                        {opp?.analysis?.relevancy_score != null && (
                          <Badge size="xs" variant="light">{opp.analysis.relevancy_score}%</Badge>
                        )}
                        {opp?.response_deadline && (
                          <Text size="xs" c="dimmed">{dayjs(opp.response_deadline).format('MMM D')}</Text>
                        )}
                        <Badge size="xs" variant="outline">P{entry.priority}</Badge>
                      </Group>
                      <Group mt="xs" gap="xs">
                        <Select
                          size="xs"
                          data={STAGES.map((s) => ({ value: s.key, label: s.label }))}
                          value={entry.stage}
                          onChange={(val) => val && val !== entry.stage && updateMutation.mutate({ id: entry.id, stage: val })}
                          style={{ flex: 1 }}
                        />
                        <Button size="xs" variant="subtle" color="red" onClick={() => deleteMutation.mutate(entry.id)}>
                          ×
                        </Button>
                      </Group>
                    </Card>
                  )
                })}
                {entries.length === 0 && (
                  <Text size="sm" c="dimmed" ta="center" py="lg">Empty</Text>
                )}
              </Stack>
            </div>
          )
        })}
      </div>
    </Stack>
  )
}
