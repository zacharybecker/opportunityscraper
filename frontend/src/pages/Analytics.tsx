import { useState } from 'react'
import {
  Title, Stack, Card, Group, Text, SimpleGrid, Select,
  Loader, Center, Badge,
} from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { getCharts } from '../api'

const COLORS = ['#228be6', '#40c057', '#fab005', '#fa5252', '#7950f2', '#15aabf']

export default function Analytics() {
  const [days, setDays] = useState('30')

  const { data, isLoading } = useQuery({
    queryKey: ['charts', days],
    queryFn: () => getCharts({ days: parseInt(days) }),
  })

  if (isLoading) return <Center h={400}><Loader /></Center>

  const relevancyDist = data?.relevancy_distribution || []
  const topNaics = data?.top_naics || []
  const pipelineData = data?.pipeline_data || []

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Analytics</Title>
        <Select
          value={days}
          onChange={(v) => v && setDays(v)}
          data={[
            { value: '7', label: 'Last 7 days' },
            { value: '30', label: 'Last 30 days' },
            { value: '90', label: 'Last 90 days' },
            { value: '365', label: 'Last year' },
          ]}
          w={160}
        />
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="sm">Win Rate</Title>
          <Group>
            <Text fw={700} size="xl" c="green">{data?.win_rate || 0}%</Text>
            <Text size="sm" c="dimmed">of {data?.total_decided || 0} decided</Text>
          </Group>
        </Card>

        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="sm">Relevancy Distribution</Title>
          {relevancyDist.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={relevancyDist}
                  dataKey="count"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  label={({ label, count }) => `${label}: ${count}`}
                >
                  {relevancyDist.map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <Text c="dimmed" size="sm">No data</Text>
          )}
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="sm">Top NAICS Codes</Title>
          {topNaics.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topNaics} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="code" width={80} />
                <Tooltip />
                <Bar dataKey="count" fill="#228be6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Text c="dimmed" size="sm">No data</Text>
          )}
        </Card>

        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="sm">Pipeline Distribution</Title>
          {pipelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={pipelineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="stage" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#40c057" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Text c="dimmed" size="sm">No data</Text>
          )}
        </Card>
      </SimpleGrid>
    </Stack>
  )
}
