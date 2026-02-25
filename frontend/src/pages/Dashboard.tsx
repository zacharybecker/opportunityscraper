import { Title, SimpleGrid, Card, Text, Group, Stack, Badge, Table, Loader, Center } from '@mantine/core'
import { IconFileSearch, IconStar, IconClock, IconKanban } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { getDashboard } from '../api'

dayjs.extend(relativeTime)

function StatCard({ title, value, icon: Icon, color }: { title: string; value: number | string; icon: any; color: string }) {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Group justify="space-between">
        <div>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>{title}</Text>
          <Text fw={700} size="xl">{value}</Text>
        </div>
        <Icon size={32} color={`var(--mantine-color-${color}-6)`} />
      </Group>
    </Card>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  })

  if (isLoading) return <Center h={400}><Loader /></Center>

  const d = data!
  const totalPipeline = Object.values(d.pipeline_counts || {}).reduce((a, b) => a + b, 0)

  return (
    <Stack>
      <Title order={2}>Dashboard</Title>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <StatCard title="Active Opportunities" value={d.active_opportunities} icon={IconFileSearch} color="blue" />
        <StatCard title="High Relevancy" value={d.high_relevancy_count} icon={IconStar} color="yellow" />
        <StatCard title="Approaching Deadlines" value={d.approaching_deadlines} icon={IconClock} color="red" />
        <StatCard title="In Pipeline" value={totalPipeline} icon={IconKanban} color="green" />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="md">Recent High-Relevancy Opportunities</Title>
          {d.recent_high_relevancy?.length ? (
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Title</Table.Th>
                  <Table.Th>Score</Table.Th>
                  <Table.Th>Agency</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {d.recent_high_relevancy.map((opp: any) => (
                  <Table.Tr key={opp.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/opportunities/${opp.id}`)}>
                    <Table.Td>{opp.title?.substring(0, 60)}...</Table.Td>
                    <Table.Td>
                      <Badge color={opp.analysis?.relevancy_score >= 80 ? 'green' : 'yellow'}>
                        {opp.analysis?.relevancy_score || 'N/A'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{opp.agency?.substring(0, 30)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed">No high-relevancy opportunities yet</Text>
          )}
        </Card>

        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="md">Upcoming Deadlines</Title>
          {d.upcoming_deadlines?.length ? (
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Title</Table.Th>
                  <Table.Th>Deadline</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {d.upcoming_deadlines.map((opp: any) => (
                  <Table.Tr key={opp.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/opportunities/${opp.id}`)}>
                    <Table.Td>{opp.title?.substring(0, 60)}...</Table.Td>
                    <Table.Td>
                      <Badge color={dayjs(opp.response_deadline).diff(dayjs(), 'day') <= 3 ? 'red' : 'blue'}>
                        {dayjs(opp.response_deadline).fromNow()}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed">No upcoming deadlines</Text>
          )}
        </Card>
      </SimpleGrid>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Title order={4} mb="md">Recent Scrape Runs</Title>
        {d.recent_scrape_runs?.length ? (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Status</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Results</Table.Th>
                <Table.Th>When</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {d.recent_scrape_runs.map((run: any) => (
                <Table.Tr key={run.id}>
                  <Table.Td>
                    <Badge color={run.status === 'completed' ? 'green' : run.status === 'failed' ? 'red' : 'yellow'}>
                      {run.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{run.trigger_type}</Table.Td>
                  <Table.Td>
                    {run.stats?.found ? `${run.stats.new} new / ${run.stats.found} found` : '-'}
                  </Table.Td>
                  <Table.Td>{dayjs(run.created_at).fromNow()}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        ) : (
          <Text c="dimmed">No scrape runs yet</Text>
        )}
      </Card>
    </Stack>
  )
}
